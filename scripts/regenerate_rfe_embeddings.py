"""
Regenerate RFE Knowledge embeddings with 2000 dimensions for HNSW index compatibility.

OpenAI text-embedding-3-large supports variable dimensions via API parameter.
pgvector HNSW index has a maximum of 2000 dimensions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import os

import asyncpg
from dotenv import load_dotenv
import httpx

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-large"
TARGET_DIMENSION = 2000
BATCH_SIZE = 50
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_raw_dsn = os.getenv("POSTGRES_DSN", "")
POSTGRES_DSN = _raw_dsn.replace("postgresql+asyncpg://", "postgresql://").replace("\\!", "!")


async def get_embedding(texts: list[str], client: httpx.AsyncClient) -> list[list[float]]:
    response = await client.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "input": texts,
            "model": EMBEDDING_MODEL,
            "dimensions": TARGET_DIMENSION,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in data["data"]]


def build_embedding_text(record: dict) -> str:
    parts = []

    if record.get("criterion"):
        parts.append(f"Criterion: {record['criterion']}")
    if record.get("issue_type"):
        parts.append(f"Issue Type: {record['issue_type']}")
    if record.get("problem_description"):
        parts.append(f"Problem: {record['problem_description']}")
    if record.get("uscis_quote"):
        parts.append(f"USCIS Quote: {record['uscis_quote']}")
    if record.get("success_response"):
        parts.append(f"Response: {record['success_response']}")
    if record.get("required_evidence"):
        evidence = record["required_evidence"]
        if isinstance(evidence, list):
            parts.append(f"Required Evidence: {', '.join(evidence)}")

    return "\n\n".join(parts)


async def regenerate_embeddings():
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)
    if not POSTGRES_DSN:
        print("ERROR: POSTGRES_DSN not set")
        sys.exit(1)

    print("Connecting to database...")
    conn = await asyncpg.connect(POSTGRES_DSN)

    try:
        print("Fetching RFE knowledge records...")
        records = await conn.fetch(
            """
            SELECT id, criterion, issue_type, uscis_quote,
                   problem_description, required_evidence, success_response
            FROM mega_agent.rfe_knowledge
        """
        )
        total = len(records)
        print(f"Found {total} records to process")

        if total == 0:
            print("No records found")
            return

        updated = 0
        errors = 0

        async with httpx.AsyncClient() as client:
            for batch_start in range(0, total, BATCH_SIZE):
                batch = records[batch_start : batch_start + BATCH_SIZE]
                batch_num = batch_start // BATCH_SIZE + 1
                total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

                print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} records)...")

                texts = [build_embedding_text(dict(r)) for r in batch]

                try:
                    embeddings = await get_embedding(texts, client)

                    for record, embedding in zip(batch, embeddings, strict=False):
                        try:
                            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                            await conn.execute(
                                """
                                UPDATE mega_agent.rfe_knowledge
                                SET embedding = $1::vector, updated_at = NOW()
                                WHERE id = $2
                            """,
                                embedding_str,
                                record["id"],
                            )
                            updated += 1
                        except Exception as e:
                            print(f"  Error updating record {record['id']}: {e}")
                            errors += 1

                    print(f"  Updated {len(batch)} records (dimension: {len(embeddings[0])})")

                except Exception as e:
                    print(f"  Error getting embeddings: {e}")
                    errors += len(batch)

                await asyncio.sleep(0.5)

        print(f"\n{'='*50}")
        print(f"COMPLETE: Updated {updated}/{total} records")
        if errors:
            print(f"ERRORS: {errors} records failed")

        # Verify new dimension
        print("\nVerifying new embedding dimensions...")
        result = await conn.fetchval(
            """
            SELECT vector_dims(embedding) FROM mega_agent.rfe_knowledge LIMIT 1
        """
        )
        print(f"New embedding dimension: {result}")

    finally:
        await conn.close()


async def create_hnsw_index():
    if not POSTGRES_DSN:
        print("ERROR: POSTGRES_DSN not set")
        return

    print("\nConnecting to database for index creation...")
    conn = await asyncpg.connect(POSTGRES_DSN)

    try:
        print("Creating HNSW index on rfe_knowledge.embedding...")

        # Drop existing index if any
        await conn.execute("DROP INDEX IF EXISTS mega_agent.idx_rfe_knowledge_embedding_hnsw;")

        # Create new HNSW index
        await conn.execute(
            """
            CREATE INDEX idx_rfe_knowledge_embedding_hnsw
            ON mega_agent.rfe_knowledge
            USING hnsw (embedding vector_cosine_ops)
            WITH (m=16, ef_construction=64);
        """
        )
        print("HNSW index created successfully!")

    except Exception as e:
        print(f"Error creating index: {e}")
        print("You may need to create the index manually via Supabase SQL editor")
    finally:
        await conn.close()


async def main():
    await regenerate_embeddings()
    await create_hnsw_index()


if __name__ == "__main__":
    print("=" * 50)
    print("RFE Knowledge Embedding Regeneration")
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Target Dimension: {TARGET_DIMENSION}")
    print("=" * 50)

    asyncio.run(main())

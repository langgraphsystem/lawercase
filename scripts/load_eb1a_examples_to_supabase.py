#!/usr/bin/env python3
"""
Load EB-1A petition examples into Supabase vector store for RAG retrieval.

This script reads the examples from knowledge_base/legal/eb1a_examples_rag.json
and loads them into the Supabase vector store with embeddings for semantic search.

Usage:
    python scripts/load_eb1a_examples_to_supabase.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.llm.supabase_embedder import get_embedder
from core.memory.models import MemoryRecord
from core.storage.supabase_vector_store import SupabaseVectorStore

# Namespace for EB-1A examples in the vector store
EB1A_EXAMPLES_NAMESPACE = "eb1a_petition_examples"


def load_examples_from_file() -> list[dict]:
    """Load examples from the JSON file."""
    examples_file = project_root / "knowledge_base" / "legal" / "eb1a_examples_rag.json"

    if not examples_file.exists():
        raise FileNotFoundError(f"Examples file not found: {examples_file}")

    with open(examples_file, encoding="utf-8") as f:
        data = json.load(f)

    return data.get("examples", [])


def create_memory_record(example: dict) -> MemoryRecord:
    """Convert an example to a MemoryRecord for storage."""

    # Combine key fields for the searchable text
    text_parts = [
        f"Criterion: {example.get('criterion', '')}",
        f"Title: {example.get('title', '')}",
        f"Field: {example.get('field', '')}",
        f"Summary: {example.get('summary', '')}",
        f"Full Description: {example.get('full_text', '')}",
    ]

    # Add key elements if present
    if key_elements := example.get("key_elements"):
        text_parts.append("Key Elements:")
        for elem in key_elements:
            text_parts.append(f"  - {elem}")

    # Add required documents if present
    if required_docs := example.get("required_documents"):
        text_parts.append("Required Documents:")
        for doc in required_docs:
            text_parts.append(f"  - {doc}")

    text = "\n".join(text_parts)

    # Create tags for filtering
    tags = [
        f"criterion:{example.get('criterion', 'unknown')}",
        f"field:{example.get('field', 'unknown')}",
        f"code:{example.get('criterion_code', 'unknown')}",
        "type:eb1a_example",
    ]

    return MemoryRecord(
        id=example.get("id", str(uuid4())),
        type="semantic",
        text=text,
        source="eb1a_petition_sample",
        tags=tags,
        salience=0.9,  # High salience for reference examples
        confidence=1.0,  # These are verified examples
        metadata={
            "example_id": example.get("id"),
            "criterion": example.get("criterion"),
            "criterion_code": example.get("criterion_code"),
            "title": example.get("title"),
            "field": example.get("field"),
            "summary": example.get("summary"),
            "key_elements": example.get("key_elements", []),
            "required_documents": example.get("required_documents", []),
            "language": example.get("language", "en"),
        },
    )


async def load_examples_to_supabase() -> dict:
    """Load all examples into Supabase vector store."""
    print("Loading EB-1A examples into Supabase...")

    # Load examples from file
    examples = load_examples_from_file()
    print(f"Found {len(examples)} examples to load")

    if not examples:
        return {"status": "error", "message": "No examples found"}

    # Create memory records
    records = [create_memory_record(ex) for ex in examples]
    print(f"Created {len(records)} memory records")

    # Get embedder
    embedder = get_embedder()

    # Generate embeddings for all records
    print("Generating embeddings...")
    texts = [r.text for r in records]
    embeddings = await embedder.embed_texts(texts)
    print(f"Generated {len(embeddings)} embeddings")

    # Initialize vector store with EB-1A examples namespace
    store = SupabaseVectorStore(namespace=EB1A_EXAMPLES_NAMESPACE)

    # Check if store is healthy
    if not await store.health_check():
        return {"status": "error", "message": "Supabase connection failed"}

    # Get current stats
    before_stats = await store.get_stats()
    print(f"Before: {before_stats['total_vectors']} vectors in namespace")

    # Upsert records with embeddings
    print("Upserting records...")
    upserted = await store.upsert(records, embeddings)
    print(f"Upserted {upserted} records")

    # Get updated stats
    after_stats = await store.get_stats()
    print(f"After: {after_stats['total_vectors']} vectors in namespace")

    return {
        "status": "success",
        "examples_loaded": len(examples),
        "records_upserted": upserted,
        "total_vectors": after_stats["total_vectors"],
        "namespace": EB1A_EXAMPLES_NAMESPACE,
    }


async def search_examples(
    query: str,
    criterion: str | None = None,
    field: str | None = None,
    topk: int = 5,
) -> list[dict]:
    """
    Search for similar examples in the vector store.

    Args:
        query: Search query text
        criterion: Optional filter by criterion (e.g., "awards", "membership")
        field: Optional filter by field (e.g., "education", "technology")
        topk: Number of results to return

    Returns:
        List of matching examples with scores
    """
    # Get embedder and generate query embedding
    embedder = get_embedder()
    query_embedding = (await embedder.embed_texts([query]))[0]

    # Build filters
    filters = {"type": "semantic"}
    if criterion:
        filters["tags"] = [f"criterion:{criterion}"]

    # Initialize vector store
    store = SupabaseVectorStore(namespace=EB1A_EXAMPLES_NAMESPACE)

    # Search
    results = await store.search(
        query_embedding,
        topk=topk,
        filters=filters,
        min_score=0.3,
    )

    return results


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Load EB-1A examples to Supabase")
    parser.add_argument(
        "--search",
        type=str,
        help="Search query to test the loaded examples",
    )
    parser.add_argument(
        "--criterion",
        type=str,
        help="Filter search by criterion (awards, membership, etc.)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all examples before loading",
    )

    args = parser.parse_args()

    # Handle clear
    if args.clear:
        print("Clearing existing examples...")
        store = SupabaseVectorStore(namespace=EB1A_EXAMPLES_NAMESPACE)
        await store.delete_all()
        print("Cleared.")

    # Load examples
    result = await load_examples_to_supabase()
    print(f"\nResult: {json.dumps(result, indent=2)}")

    # Test search if query provided
    if args.search:
        print(f"\nSearching for: {args.search}")
        results = await search_examples(
            args.search,
            criterion=args.criterion,
            topk=3,
        )
        print(f"\nFound {len(results)} results:")
        for i, r in enumerate(results, 1):
            print(f"\n{i}. Score: {r['score']:.3f}")
            print(f"   ID: {r['record_id']}")
            if metadata := r.get("metadata", {}):
                print(f"   Title: {metadata.get('title', 'N/A')}")
                text = metadata.get("text", "")[:200]
                print(f"   Text: {text}...")


if __name__ == "__main__":
    asyncio.run(main())

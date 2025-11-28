#!/usr/bin/env python3
"""Simple test to verify semantic memory writes to database using OpenAI embeddings."""
from __future__ import annotations

import asyncio
from datetime import datetime
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from core.memory.memory_manager import MemoryManager
from core.memory.models import MemoryRecord
from core.memory.stores.supabase_semantic_store import SupabaseSemanticStore

load_dotenv()


# Simple embedder using OpenAI directly
class SimpleOpenAIEmbedder:
    """Simple OpenAI embedder for testing."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "text-embedding-3-large"
        self.dimension = 1536

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for documents."""
        if not texts:
            return []

        response = await self.client.embeddings.create(
            input=texts,
            model=self.model,
        )

        return [item.embedding for item in response.data]

    async def aembed_query(self, text: str) -> list[float]:
        """Generate embedding for a query."""
        embeddings = await self.aembed_documents([text])
        return embeddings[0] if embeddings else [0.0] * self.dimension


async def test_memory():
    """Test semantic memory persistence."""
    print("=" * 80)
    print("TESTING SEMANTIC MEMORY WITH SIMPLE OPENAI EMBEDDER")
    print("=" * 80)

    # Create simple embedder
    print("\n1. Creating embedder...")
    embedder = SimpleOpenAIEmbedder()
    print("✅ Embedder created")

    # Create semantic store with our embedder
    print("\n2. Creating SupabaseSemanticStore...")
    try:
        semantic_store = SupabaseSemanticStore(embedder=embedder)
        print("✅ SupabaseSemanticStore created")
    except Exception as e:
        print(f"❌ Failed to create store: {e}")
        return False

    # Create memory manager
    print("\n3. Creating MemoryManager...")
    memory_manager = MemoryManager(semantic=semantic_store)
    print("✅ MemoryManager created")

    # Create test record
    test_case_id = "test-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    test_user_id = "7314014306"

    print("\n4. Creating test record...")
    print(f"   User: {test_user_id}")
    print(f"   Case: {test_case_id}")

    test_record = MemoryRecord(
        text="TEST: Sample intake answer - Full Name is John Doe",
        user_id=test_user_id,
        case_id=test_case_id,
        type="semantic",
        source="intake_questionnaire",
        tags=["intake", "test"],
        metadata={
            "question_id": "full_name",
            "raw_response": "John Doe",
        },
    )
    print("✅ Test record created")

    # Write to memory
    print("\n5. Writing to database...")
    try:
        written = await memory_manager.awrite([test_record])
        print(f"✅ Written {len(written)} record(s)")
        print(f"   Record ID: {written[0].id}")
    except Exception as e:
        print(f"❌ Write failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Verify in database
    print("\n6. Verifying in database...")
    try:
        from sqlalchemy import text

        from core.storage.connection import get_db_manager

        db = get_db_manager()
        async with db.session() as session:
            stmt = text(
                """
                SELECT record_id, text, user_id, metadata_json->>'case_id' as case_id
                FROM mega_agent.semantic_memory
                WHERE user_id = :user_id
                  AND tags @> ARRAY['test']::text[]
                ORDER BY created_at DESC
                LIMIT 1
            """
            )
            result = await session.execute(stmt, {"user_id": test_user_id})
            row = result.fetchone()

            if row:
                print("✅ Record verified in database!")
                print(f"   ID: {row[0]}")
                print(f"   Text: {row[1][:60]}...")
                print(f"   User: {row[2]}")
                print(f"   Case: {row[3]}")

                if row[3] == test_case_id:
                    print("   ✅ case_id matches!")
                else:
                    print("   ❌ case_id mismatch!")
                    return False
            else:
                print("❌ Record NOT found in database!")
                return False

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("✅ TEST PASSED - Memory system is working!")
    print("=" * 80)
    print("\n✅ Fix confirmed:")
    print("   1. SupabaseSemanticStore saves to database")
    print("   2. case_id is preserved in metadata")
    print("   3. Records can be queried from Supabase")
    print("\n💡 Bot is ready to save intake answers!")

    return True


if __name__ == "__main__":
    import sys

    result = asyncio.run(test_memory())
    sys.exit(0 if result else 1)

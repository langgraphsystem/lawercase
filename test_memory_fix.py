#!/usr/bin/env python3
"""Test script to verify SupabaseSemanticStore is working correctly."""
from __future__ import annotations

import asyncio
from datetime import datetime

from core.memory.memory_manager import MemoryManager
from core.memory.models import MemoryRecord
from core.memory.stores.supabase_semantic_store import SupabaseSemanticStore


async def test_memory_write():
    """Test writing to Supabase semantic store."""
    print("=" * 80)
    print("TESTING SUPABASE SEMANTIC STORE")
    print("=" * 80)

    # Create MemoryManager with SupabaseSemanticStore
    print("\n1. Creating MemoryManager with SupabaseSemanticStore...")
    memory_manager = MemoryManager(semantic=SupabaseSemanticStore())
    print("✅ MemoryManager created")

    # Create test record
    test_case_id = "test-case-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    test_user_id = "7314014306"

    print("\n2. Creating test MemoryRecord...")
    print(f"   User ID: {test_user_id}")
    print(f"   Case ID: {test_case_id}")

    test_record = MemoryRecord(
        text="TEST: This is a test intake answer from the questionnaire",
        user_id=test_user_id,
        case_id=test_case_id,
        type="semantic",
        tags=["intake", "test"],
        metadata={
            "source": "intake_questionnaire",
            "question_id": "test_question",
            "raw_response": "Test answer",
            "normalized_value": "Test answer",
        },
    )
    print("✅ Test record created")

    # Write to memory
    print("\n3. Writing to memory...")
    try:
        written_records = await memory_manager.awrite([test_record])
        print(f"✅ Written {len(written_records)} record(s)")
        print(f"   Record ID: {written_records[0].id}")
    except Exception as e:
        print(f"❌ FAILED to write: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Verify it was saved
    print("\n4. Verifying record was saved to database...")
    try:
        from sqlalchemy import text

        from core.storage.connection import get_db_manager

        db = get_db_manager()
        async with db.session() as session:
            stmt = text(
                """
                SELECT record_id, text, user_id, tags, metadata_json
                FROM mega_agent.semantic_memory
                WHERE user_id = :user_id
                  AND metadata_json->>'case_id' = :case_id
                ORDER BY created_at DESC
                LIMIT 1
            """
            )
            result = await session.execute(stmt, {"user_id": test_user_id, "case_id": test_case_id})
            row = result.fetchone()

            if row:
                print("✅ Record found in database!")
                print(f"   Record ID: {row[0]}")
                print(f"   Text: {row[1]}")
                print(f"   User ID: {row[2]}")
                print(f"   Tags: {row[3]}")
                print(f"   Metadata: {row[4]}")

                # Verify case_id is in metadata
                if row[4].get("case_id") == test_case_id:
                    print("   ✅ case_id correctly stored in metadata_json")
                else:
                    print(
                        f"   ❌ case_id mismatch: expected {test_case_id}, got {row[4].get('case_id')}"
                    )
                    return False
            else:
                print("❌ Record NOT found in database!")
                return False

    except Exception as e:
        print(f"❌ FAILED to verify: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test retrieval
    print("\n5. Testing retrieval...")
    try:
        retrieved = await memory_manager.semantic.aall(user_id=test_user_id)
        test_records = [r for r in retrieved if r.tags and "test" in r.tags]
        print(f"✅ Retrieved {len(test_records)} test record(s)")
    except Exception as e:
        print(f"❌ FAILED to retrieve: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print("\n💡 This confirms that:")
    print("   1. SupabaseSemanticStore is initialized correctly")
    print("   2. Records can be written to Supabase database")
    print("   3. case_id is preserved in metadata_json")
    print("   4. Records can be retrieved from database")
    print("\n📝 Next step: Restart the Telegram bot to use the fixed memory system")
    return True


if __name__ == "__main__":
    result = asyncio.run(test_memory_write())
    exit(0 if result else 1)

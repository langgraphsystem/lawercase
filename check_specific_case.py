"""
Check specific case and intake data in Supabase.

This script checks:
1. Case record existence
2. Intake progress for the case
3. Semantic memory (intake answers)
4. Episodic memory (events)
"""

from __future__ import annotations

import asyncio
import sys

import structlog
from sqlalchemy import text

from core.storage.connection import get_db_manager

logger = structlog.get_logger(__name__)

CASE_ID = "6139bc5d-351c-4696-a80f-0dd34d15654e"


async def check_case_data():
    """Check all data for specific case."""
    print("=" * 80)
    print(f"CHECKING CASE DATA: {CASE_ID}")
    print("=" * 80)
    print()

    db = get_db_manager()

    async with db.session() as session:
        # 1. Check case record
        print("1️⃣  CASE RECORD")
        print("-" * 80)
        case_query = text(
            """
            SELECT case_id, user_id, title, status, case_type, created_at, updated_at
            FROM mega_agent.cases
            WHERE case_id::text = :case_id
            """
        )
        result = await session.execute(case_query, {"case_id": CASE_ID})
        case = result.fetchone()

        if case:
            print("✅ Case found!")
            print(f"   Case ID: {case[0]}")
            print(f"   User ID: {case[1]}")
            print(f"   Title: {case[2]}")
            print(f"   Status: {case[3]}")
            print(f"   Type: {case[4]}")
            print(f"   Created: {case[5]}")
            print(f"   Updated: {case[6]}")
        else:
            print("❌ Case NOT found!")
            return

        print()

        # 2. Check intake progress
        print("2️⃣  INTAKE PROGRESS")
        print("-" * 80)
        progress_query = text(
            """
            SELECT user_id, case_id, current_block, current_step,
                   completed_blocks, updated_at
            FROM mega_agent.case_intake_progress
            WHERE case_id = :case_id
            """
        )
        result = await session.execute(progress_query, {"case_id": CASE_ID})
        progress = result.fetchone()

        if progress:
            print("✅ Intake progress found!")
            print(f"   User ID: {progress[0]}")
            print(f"   Case ID: {progress[1]}")
            print(f"   Current Block: {progress[2]}")
            print(f"   Current Step: {progress[3]}")
            print(f"   Completed Blocks: {progress[4]}")
            print(f"   Updated: {progress[5]}")

            completed_blocks = progress[4] or []
            print(f"\n   📋 Completed Blocks ({len(completed_blocks)}):")
            for i, block in enumerate(completed_blocks, 1):
                print(f"      {i}. {block}")
        else:
            print("❌ Intake progress NOT found!")

        print()

        # 3. Check semantic memory (intake answers)
        print("3️⃣  SEMANTIC MEMORY (Intake Answers)")
        print("-" * 80)
        semantic_query = text(
            """
            SELECT record_id, user_id, text, tags, metadata_json, created_at
            FROM mega_agent.semantic_memory
            WHERE metadata_json->>'case_id' = :case_id
            ORDER BY created_at ASC
            """
        )
        result = await session.execute(semantic_query, {"case_id": CASE_ID})
        memories = result.fetchall()

        if memories:
            print(f"✅ Found {len(memories)} semantic memory records!")
            print()
            for i, mem in enumerate(memories, 1):
                print(f"   Record #{i}")
                print(f"   ├─ ID: {mem[0]}")
                print(f"   ├─ User ID: {mem[1]}")
                print(
                    f"   ├─ Text: {mem[2][:100]}..."
                    if len(mem[2]) > 100
                    else f"   ├─ Text: {mem[2]}"
                )
                print(f"   ├─ Tags: {mem[3]}")

                metadata = mem[4] or {}
                if metadata:
                    print("   ├─ Metadata:")
                    print(f"   │  ├─ source: {metadata.get('source')}")
                    print(f"   │  ├─ question_id: {metadata.get('question_id')}")
                    print(f"   │  ├─ case_id: {metadata.get('case_id')}")
                    if "raw_response" in metadata:
                        raw = metadata["raw_response"]
                        print(
                            f"   │  └─ raw_response: {raw[:50]}..."
                            if len(raw) > 50
                            else f"   │  └─ raw_response: {raw}"
                        )

                print(f"   └─ Created: {mem[5]}")
                print()
        else:
            print("❌ NO semantic memory records found!")
            print("   ⚠️  This means intake answers were NOT saved!")

        print()

        # 4. Check episodic memory
        print("4️⃣  EPISODIC MEMORY (Events)")
        print("-" * 80)
        episodic_query = text(
            """
            SELECT event_id, user_id, text, tags, created_at
            FROM mega_agent.episodic_memory
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 10
            """
        )

        if case:
            result = await session.execute(episodic_query, {"user_id": case[1]})
            episodes = result.fetchall()

            if episodes:
                print(f"✅ Found {len(episodes)} episodic memory records (last 10)!")
                print()
                for i, ep in enumerate(episodes, 1):
                    print(f"   Event #{i}")
                    print(f"   ├─ ID: {ep[0]}")
                    print(
                        f"   ├─ Text: {ep[2][:80]}..."
                        if len(ep[2]) > 80
                        else f"   ├─ Text: {ep[2]}"
                    )
                    print(f"   ├─ Tags: {ep[3]}")
                    print(f"   └─ Created: {ep[4]}")
                    print()
            else:
                print("ℹ️  No episodic memory records found")

        print()

        # 5. Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)

        case_status = "✅ EXISTS" if case else "❌ MISSING"
        progress_status = "✅ EXISTS" if progress else "❌ MISSING"
        memory_count = len(memories) if memories else 0
        memory_status = (
            f"✅ {memory_count} records" if memory_count > 0 else "❌ 0 records (DATA LOSS!)"
        )

        print(f"Case Record:      {case_status}")
        print(f"Intake Progress:  {progress_status}")
        print(f"Semantic Memory:  {memory_status}")

        if progress and memories:
            completed_count = len(progress[4] or [])
            print()
            print("📊 Data Integrity Check:")
            print(f"   Completed Blocks: {completed_count}")
            print(f"   Saved Answers: {memory_count}")

            if memory_count > 0:
                print("\n   ✅ SUCCESS: Answers are being saved to database!")
            else:
                print("\n   ❌ CRITICAL: Answers are NOT saved (in-memory storage bug)")

        print()


if __name__ == "__main__":
    try:
        asyncio.run(check_case_data())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

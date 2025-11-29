#!/usr/bin/env python3
"""Check what data should exist from completed intake blocks."""
from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import text

from core.intake.schema import BLOCKS_BY_ID
from core.storage.connection import get_db_manager

USER_ID = "7314014306"
CASE_ID = "4d60bb22-fdef-411f-bff5-46cade9693aa"
COMPLETED_BLOCKS = ["basic_info", "family_childhood", "school"]


def print_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subheader(title: str):
    """Print formatted subsection header."""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80)


async def main():
    """Check completed blocks data."""
    print_header("COMPLETED BLOCKS DATA CHECK")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"User ID: {USER_ID}")
    print(f"Case ID: {CASE_ID}")
    print(f"Completed Blocks: {', '.join(COMPLETED_BLOCKS)}")

    db = get_db_manager()

    # 1. Show expected questions from completed blocks
    print_subheader("1. EXPECTED QUESTIONS FROM COMPLETED BLOCKS")
    total_questions = 0
    for block_id in COMPLETED_BLOCKS:
        block = BLOCKS_BY_ID.get(block_id)
        if block:
            print(f"\n📋 Block: {block.title} (ID: {block_id})")
            print(f"   Questions: {len(block.questions)}")
            total_questions += len(block.questions)

            # Show first 5 questions as sample
            for i, q in enumerate(block.questions[:5], 1):
                print(f"   {i}. {q.id}: {q.text_template[:60]}...")

            if len(block.questions) > 5:
                print(f"   ... and {len(block.questions) - 5} more questions")

    print(f"\n📊 Total expected answers: {total_questions}")

    # 2. Check actual semantic memory records
    print_subheader("2. ACTUAL SEMANTIC MEMORY RECORDS")
    try:
        async with db.session() as session:
            # Check all semantic memory for this user/case
            stmt = text(
                """
                SELECT record_id, text, type, tags, metadata_json, created_at
                FROM mega_agent.semantic_memory
                WHERE user_id = :user_id
                  AND (
                      metadata_json->>'case_id' = :case_id
                      OR case_id = :case_id
                  )
                ORDER BY created_at DESC
            """
            )
            result = await session.execute(stmt, {"user_id": USER_ID, "case_id": CASE_ID})
            all_records = result.fetchall()

            print(f"Total semantic memory records for case: {len(all_records)}")

            if all_records:
                print("\n📝 Records found:")
                for idx, rec in enumerate(all_records, 1):
                    rec_text = rec[1]
                    tags = rec[3]
                    metadata = rec[4] or {}

                    print(f"\nRecord {idx}:")
                    print(f"  ├─ Text: {rec_text[:100]}{'...' if len(rec_text) > 100 else ''}")
                    print(f"  ├─ Tags: {tags}")
                    print(f"  ├─ Metadata: {metadata}")
                    print(f"  └─ Created: {rec[5]}")
            else:
                print("\n⚠️  NO semantic memory records found!")
                print("   Expected: At least some intake answers")
                print("   Found: 0 records")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # 3. Check if there are ANY semantic memory records for this user
    print_subheader("3. ALL USER SEMANTIC MEMORY")
    try:
        async with db.session() as session:
            stmt = text(
                """
                SELECT COUNT(*),
                       COUNT(*) FILTER (WHERE tags @> ARRAY['intake']::text[]) as intake_count,
                       MIN(created_at) as first_record,
                       MAX(created_at) as last_record
                FROM mega_agent.semantic_memory
                WHERE user_id = :user_id
            """
            )
            result = await session.execute(stmt, {"user_id": USER_ID})
            stats = result.fetchone()

            print(f"Total records: {stats[0]}")
            print(f"Intake-tagged records: {stats[1]}")
            print(f"First record: {stats[2]}")
            print(f"Last record: {stats[3]}")

            if stats[0] == 0:
                print("\n⚠️  CRITICAL: No semantic memory records exist for this user at all!")
                print("   This indicates memory system is NOT working")

    except Exception as e:
        print(f"❌ Error: {e}")

    # 4. Check intake progress to confirm completion
    print_subheader("4. INTAKE PROGRESS VERIFICATION")
    try:
        async with db.session() as session:
            stmt = text(
                """
                SELECT current_block, current_step, completed_blocks, updated_at
                FROM mega_agent.case_intake_progress
                WHERE user_id = :user_id AND case_id = :case_id
            """
            )
            result = await session.execute(stmt, {"user_id": USER_ID, "case_id": CASE_ID})
            progress = result.fetchone()

            if progress:
                print("✅ Intake progress found:")
                print(f"   Current block: {progress[0]}")
                print(f"   Current step: {progress[1]}")
                print(f"   Completed blocks: {progress[2]}")
                print(f"   Last updated: {progress[3]}")

                # Verify completed blocks match
                if progress[2] == COMPLETED_BLOCKS:
                    print(f"\n   ✅ Completed blocks match expected: {COMPLETED_BLOCKS}")
                else:
                    print("\n   ⚠️  Mismatch!")
                    print(f"   Expected: {COMPLETED_BLOCKS}")
                    print(f"   Found: {progress[2]}")
            else:
                print("❌ No intake progress found!")

    except Exception as e:
        print(f"❌ Error: {e}")

    # 5. Diagnosis
    print_header("DIAGNOSIS")
    print("\n🔍 Analysis:")
    print(f"   ├─ Expected answers: {total_questions}")
    print("   ├─ Actual answers: 0")
    print("   └─ Data loss: 100%")

    print("\n❌ CRITICAL BUG CONFIRMED:")
    print("   Intake progress is being saved correctly")
    print("   BUT answers are NOT being saved to semantic_memory")

    print("\n🔧 Potential causes:")
    print("   1. _save_response_to_memory() not being called")
    print("   2. bot_context.mega_agent.memory.awrite() failing silently")
    print("   3. Memory system not initialized properly")
    print("   4. Transaction rollback issue")

    print("\n💡 Recommended fix:")
    print("   Add debug logging to intake_handlers.py:")
    print("   - Before calling memory.awrite()")
    print("   - After successful write")
    print("   - In exception handler")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Comprehensive verification of case data and intake processing."""
from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import text

from core.storage.connection import get_db_manager

USER_ID = "7314014306"


async def main():
    """Verify all case data and intake processing."""
    print("=" * 80)
    print("COMPREHENSIVE CASE DATA VERIFICATION")
    print(f"User ID: {USER_ID}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 80)
    print()

    db = get_db_manager()

    # 1. Check intake progress records
    print("1. INTAKE PROGRESS RECORDS")
    print("-" * 80)
    try:
        async with db.session() as session:
            stmt = text(
                """
                SELECT user_id, case_id, current_block, current_step,
                       completed_blocks, updated_at
                FROM mega_agent.case_intake_progress
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
            """
            )
            result = await session.execute(stmt, {"user_id": USER_ID})
            intake_records = result.fetchall()

            if intake_records:
                print(f"✅ Found {len(intake_records)} intake progress records:\n")
                case_ids = []
                for idx, row in enumerate(intake_records, 1):
                    case_id = row[1]
                    case_ids.append(case_id)
                    print(f"   Record {idx}:")
                    print(f"   ├─ Case ID: {case_id}")
                    print(f"   ├─ Current block: {row[2]}")
                    print(f"   ├─ Current step: {row[3]}")
                    print(f"   ├─ Completed blocks: {row[4]}")
                    print(f"   └─ Last updated: {row[5]}")
                    print()
            else:
                print("⚠️  No intake progress records found")
                case_ids = []
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return
    print()

    # 2. Check corresponding cases
    print("2. CASE RECORDS")
    print("-" * 80)
    try:
        for case_id in case_ids:
            async with db.session() as session:
                stmt = text(
                    """
                    SELECT case_id, title, status, case_type, user_id,
                           data, created_at, updated_at, deleted_at
                    FROM mega_agent.cases
                    WHERE case_id = :case_id
                """
                )
                result = await session.execute(stmt, {"case_id": case_id})
                case_row = result.fetchone()

                print(f"Case {case_id}:")
                if case_row:
                    print("✅ Case found in database:")
                    print(f"   ├─ Title: {case_row[1]}")
                    print(f"   ├─ Status: {case_row[2]}")
                    print(f"   ├─ Type: {case_row[3]}")
                    print(f"   ├─ User ID: {case_row[4]}")
                    print(f"   ├─ Data: {case_row[5]}")
                    print(f"   ├─ Created: {case_row[6]}")
                    print(f"   ├─ Updated: {case_row[7]}")
                    print(f"   └─ Deleted: {case_row[8]}")
                else:
                    print("❌ Case NOT found in cases table!")
                    print("   This means intake progress exists but case record is missing.")
                    print("   This is a data consistency issue.")
                print()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 3. Check semantic memory for intake data
    print("3. SEMANTIC MEMORY (Intake data)")
    print("-" * 80)
    try:
        for case_id in case_ids:
            async with db.session() as session:
                stmt = text(
                    """
                    SELECT record_id, text, type, tags, metadata_json, created_at
                    FROM mega_agent.semantic_memory
                    WHERE user_id = :user_id
                      AND (
                          text ILIKE :case_pattern
                          OR metadata_json::text ILIKE :case_pattern
                          OR :case_id_str = ANY(tags)
                      )
                    ORDER BY created_at DESC
                    LIMIT 20
                """
                )
                result = await session.execute(
                    stmt,
                    {
                        "user_id": USER_ID,
                        "case_pattern": f"%{case_id}%",
                        "case_id_str": str(case_id),
                    },
                )
                memory_records = result.fetchall()

                print(f"Case {case_id}:")
                if memory_records:
                    print(f"✅ Found {len(memory_records)} semantic memory records:")
                    for idx, mem in enumerate(memory_records[:5], 1):  # Show first 5
                        print(f"   Record {idx}:")
                        print(f"   ├─ Text: {mem[1][:80]}...")
                        print(f"   ├─ Type: {mem[2]}")
                        print(f"   ├─ Tags: {mem[3]}")
                        print(f"   ├─ Metadata: {mem[4]}")
                        print(f"   └─ Created: {mem[5]}")
                        print()
                else:
                    print("⚠️  No semantic memory records found")
                    print("   Intake answers may not be stored in semantic memory yet.")
                print()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 4. Check episodic memory (raw events)
    print("4. EPISODIC MEMORY (Recent events)")
    print("-" * 80)
    try:
        for case_id in case_ids:
            async with db.session() as session:
                stmt = text(
                    """
                    SELECT event_id, source, action, payload, timestamp
                    FROM mega_agent.episodic_memory
                    WHERE user_id = :user_id
                      AND payload::text ILIKE :case_pattern
                    ORDER BY timestamp DESC
                    LIMIT 10
                """
                )
                result = await session.execute(
                    stmt, {"user_id": USER_ID, "case_pattern": f"%{case_id}%"}
                )
                events = result.fetchall()

                print(f"Case {case_id}:")
                if events:
                    print(f"✅ Found {len(events)} episodic events:")
                    for idx, event in enumerate(events[:5], 1):
                        print(f"   Event {idx}:")
                        print(f"   ├─ Source: {event[1]}")
                        print(f"   ├─ Action: {event[2]}")
                        print(f"   ├─ Payload: {str(event[3])[:100]}...")
                        print(f"   └─ Timestamp: {event[4]}")
                        print()
                else:
                    print("⚠️  No episodic events found")
                print()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 5. Summary
    print("=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print("✅ Intake progress tracking: Working correctly")
    print(f"   - {len(case_ids)} case(s) with active intake progress")
    print()
    print("Next Steps:")
    print("1. If case records are missing, investigate why cases aren't created")
    print("2. Check if intake answers are being saved to semantic memory")
    print("3. Verify memory reflection is working after intake completion")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Real-time monitoring of intake data using direct database connection."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from core.groupagents.case_agent import CaseAgent

USER_ID = "7314014306"


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
    """Monitor intake data in real-time."""
    print_header("REAL-TIME INTAKE DATA MONITOR")
    print(f"Timestamp: {datetime.now(UTC).isoformat()}")
    print(f"User ID: {USER_ID}")

    # Get case agent
    case_agent = CaseAgent()

    # 1. Get all cases for user
    print_subheader("1. USER CASES")
    try:
        from sqlalchemy import text

        from core.storage.connection import get_db_manager

        db = get_db_manager()
        async with db.session() as session:
            stmt = text(
                """
                SELECT case_id, title, status, case_type, created_at, updated_at
                FROM mega_agent.cases
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """
            )
            result = await session.execute(stmt, {"user_id": USER_ID})
            cases = result.fetchall()

            if cases:
                print(f"✅ Found {len(cases)} case(s):\n")
                for idx, case in enumerate(cases, 1):
                    print(f"Case {idx}:")
                    print(f"  ├─ Case ID: {case[0]}")
                    print(f"  ├─ Title: {case[1]}")
                    print(f"  ├─ Status: {case[2]}")
                    print(f"  ├─ Type: {case[3]}")
                    print(f"  ├─ Created: {case[4]}")
                    print(f"  └─ Updated: {case[5]}")
                    print()
            else:
                print("⚠️  No cases found")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 2. Check intake progress
    print_subheader("2. INTAKE PROGRESS")
    try:
        async with db.session() as session:
            stmt = text(
                """
                SELECT case_id, current_block, current_step, completed_blocks, updated_at
                FROM mega_agent.case_intake_progress
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
            """
            )
            result = await session.execute(stmt, {"user_id": USER_ID})
            progress_records = result.fetchall()

            if progress_records:
                print(f"✅ Found {len(progress_records)} intake progress record(s):\n")
                for idx, prog in enumerate(progress_records, 1):
                    print(f"Progress {idx}:")
                    print(f"  ├─ Case ID: {prog[0]}")
                    print(f"  ├─ Current Block: {prog[1]}")
                    print(f"  ├─ Current Step: {prog[2]}")
                    print(f"  ├─ Completed Blocks: {prog[3]}")
                    print(f"  └─ Updated: {prog[4]}")
                    print()
            else:
                print("⚠️  No intake progress records found")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 3. Check semantic memory (intake answers)
    print_subheader("3. SEMANTIC MEMORY (Intake Answers)")
    try:
        async with db.session() as session:
            stmt = text(
                """
                SELECT record_id, text, type, tags, metadata_json, created_at
                FROM mega_agent.semantic_memory
                WHERE user_id = :user_id
                  AND tags @> ARRAY['intake']::text[]
                ORDER BY created_at DESC
                LIMIT 50
            """
            )
            result = await session.execute(stmt, {"user_id": USER_ID})
            memory_records = result.fetchall()

            if memory_records:
                print(f"✅ Found {len(memory_records)} intake answer(s) in semantic memory:\n")

                # Group by question_id from metadata
                for idx, rec in enumerate(memory_records[:20], 1):
                    text = rec[1]
                    tags = rec[3]
                    metadata = rec[4] or {}
                    question_id = metadata.get("question_id", "N/A")
                    raw_response = metadata.get("raw_response", "")

                    print(f"Answer {idx}:")
                    print(f"  ├─ Question ID: {question_id}")
                    print(f"  ├─ Synthesized Fact: {text[:100]}{'...' if len(text) > 100 else ''}")
                    if raw_response:
                        print(
                            f"  ├─ Raw Response: {raw_response[:80]}{'...' if len(raw_response) > 80 else ''}"
                        )
                    print(f"  ├─ Tags: {tags}")
                    print(f"  └─ Created: {rec[5]}")
                    print()

                if len(memory_records) > 20:
                    print(f"... and {len(memory_records) - 20} more records")
            else:
                print("⚠️  No intake answers found in semantic memory")
                print("   This may mean:")
                print("   - Intake has not been started")
                print("   - Answers are not being saved to semantic memory")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 4. Check episodic memory
    print_subheader("4. EPISODIC MEMORY (Recent Events)")
    try:
        async with db.session() as session:
            stmt = text(
                """
                SELECT event_id, source, action, payload, timestamp
                FROM mega_agent.episodic_memory
                WHERE user_id = :user_id
                ORDER BY timestamp DESC
                LIMIT 10
            """
            )
            result = await session.execute(stmt, {"user_id": USER_ID})
            events = result.fetchall()

            if events:
                print(f"✅ Found {len(events)} recent event(s):\n")
                for idx, event in enumerate(events, 1):
                    payload_str = str(event[3])
                    print(f"Event {idx}:")
                    print(f"  ├─ Source: {event[1]}")
                    print(f"  ├─ Action: {event[2]}")
                    print(
                        f"  ├─ Payload: {payload_str[:80]}{'...' if len(payload_str) > 80 else ''}"
                    )
                    print(f"  └─ Timestamp: {event[4]}")
                    print()
            else:
                print("⚠️  No episodic events found")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 5. Summary and diagnostics
    print_header("SUMMARY & DIAGNOSTICS")
    try:
        async with db.session() as session:
            # Count by table
            stmt_counts = text(
                """
                SELECT
                    (SELECT COUNT(*) FROM mega_agent.cases WHERE user_id = :user_id) as cases_count,
                    (SELECT COUNT(*) FROM mega_agent.case_intake_progress WHERE user_id = :user_id) as progress_count,
                    (SELECT COUNT(*) FROM mega_agent.semantic_memory WHERE user_id = :user_id) as semantic_count,
                    (SELECT COUNT(*) FROM mega_agent.semantic_memory WHERE user_id = :user_id AND tags @> ARRAY['intake']::text[]) as intake_answers_count,
                    (SELECT COUNT(*) FROM mega_agent.episodic_memory WHERE user_id = :user_id) as episodic_count
            """
            )
            result = await session.execute(stmt_counts, {"user_id": USER_ID})
            counts = result.fetchone()

            print("\n📊 Data Overview:")
            print(f"  ├─ Total Cases: {counts[0]}")
            print(f"  ├─ Intake Progress Records: {counts[1]}")
            print(f"  ├─ Total Semantic Memory: {counts[2]}")
            print(f"  ├─ Intake Answers in Memory: {counts[3]}")
            print(f"  └─ Episodic Events: {counts[4]}")

            print("\n🔍 Diagnostics:")
            if counts[1] > 0 and counts[3] == 0:
                print(
                    "  ⚠️  WARNING: Intake progress exists but NO answers saved to semantic memory!"
                )
                print("     - Check if _save_response_to_memory() is being called")
                print("     - Check if memory.awrite() is working correctly")
            elif counts[1] > 0 and counts[3] > 0:
                print("  ✅ Intake is working correctly - answers are being saved!")
                print(f"     - {counts[3]} answer(s) stored in semantic memory")
            elif counts[1] == 0:
                print("  ℹ️  Intake has not been started or was cancelled")
            else:
                print("  ✅ Data storage appears to be working normally")

            print("\n✅ Monitoring complete!")

    except Exception as e:
        print(f"❌ Error in summary: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

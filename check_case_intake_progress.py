#!/usr/bin/env python3
"""Check intake progress and data for specific case."""
from __future__ import annotations

import asyncio
from datetime import datetime

from core.groupagents.case_agent import CaseAgent
from core.memory.memory_manager import MemoryManager
from core.storage.intake_progress import get_progress

CASE_ID = "4d60bb22-fdef-411f-bff5-46cade9693aa"
USER_ID = "7314014306"  # Your Telegram user ID


async def main():
    """Check case intake progress and related data."""
    print("=" * 80)
    print("CASE INTAKE PROGRESS CHECK")
    print(f"Case ID: {CASE_ID}")
    print(f"User ID: {USER_ID}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 80)
    print()

    # 1. Check case details
    print("1. CASE DETAILS")
    print("-" * 80)
    try:
        case_agent = CaseAgent()
        case = await case_agent.aget_case(CASE_ID)
        if case:
            print("✅ Case found:")
            print(f"   Title: {case.title}")
            print(f"   Status: {case.status}")
            print(f"   Type: {case.case_type}")
            print(f"   Client ID: {case.client_id}")
            print(f"   Created: {case.created_at}")
            print(f"   Updated: {case.updated_at}")
            if case.metadata:
                print(f"   Metadata: {case.metadata}")
        else:
            print("❌ Case not found in database")
            return
    except Exception as e:
        print(f"❌ Error fetching case: {e}")
        import traceback

        traceback.print_exc()
        return
    print()

    # 2. Check intake progress
    print("2. INTAKE PROGRESS")
    print("-" * 80)
    try:
        progress = await get_progress(USER_ID, CASE_ID)
        if progress:
            print("✅ Intake progress found:")
            print(f"   Current block: {progress.current_block}")
            print(f"   Current step: {progress.current_step}")
            print(f"   Completed blocks: {progress.completed_blocks}")
            print(f"   Updated at: {progress.updated_at}")

            # Calculate progress percentage
            from core.intake.schema import BLOCKS_BY_ID

            block = BLOCKS_BY_ID.get(progress.current_block)
            if block:
                total_questions = len(block.questions)
                percent = (
                    (progress.current_step / total_questions * 100) if total_questions > 0 else 0
                )
                print(
                    f"   Block progress: {progress.current_step}/{total_questions} ({percent:.1f}%)"
                )
        else:
            print("⚠️  No intake progress found (not started or completed)")
    except Exception as e:
        print(f"❌ Error fetching intake progress: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 3. Check semantic memory for this case
    print("3. SEMANTIC MEMORY (Case-specific facts)")
    print("-" * 80)
    try:
        memory_manager = MemoryManager(
            user_id=USER_ID,
            enable_embeddings=False,  # Faster check without embeddings
        )

        # Search for facts related to this case
        results = await memory_manager.semantic_store.asearch(query=f"case_id:{CASE_ID}", limit=10)

        if results:
            print(f"✅ Found {len(results)} semantic memory records:")
            for idx, record in enumerate(results, 1):
                print(f"\n   Record {idx}:")
                print(f"   Text: {record.text[:100]}...")
                print(f"   Tags: {record.tags}")
                if record.metadata:
                    print(f"   Metadata: {record.metadata}")
                print(f"   Created: {record.created_at}")
        else:
            print("⚠️  No semantic memory records found for this case")
    except Exception as e:
        print(f"❌ Error fetching semantic memory: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 4. Check episodic memory (raw events)
    print("4. EPISODIC MEMORY (Recent events)")
    print("-" * 80)
    try:
        # Get recent events from episodic store
        events = await memory_manager.episodic_store.aget_recent(limit=20)

        case_events = [e for e in events if CASE_ID in str(e.get("text", ""))]

        if case_events:
            print(f"✅ Found {len(case_events)} episodic events related to this case:")
            for idx, event in enumerate(case_events[:5], 1):  # Show first 5
                print(f"\n   Event {idx}:")
                print(f"   Text: {event.get('text', '')[:100]}...")
                print(f"   Event type: {event.get('event_type', 'N/A')}")
                print(f"   Timestamp: {event.get('timestamp', 'N/A')}")
        else:
            print("⚠️  No episodic events found for this case")
    except Exception as e:
        print(f"❌ Error fetching episodic memory: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 5. Check database directly for intake answers
    print("5. DATABASE CHECK (Direct SQL query)")
    print("-" * 80)
    try:
        from sqlalchemy import text

        from core.storage.connection import get_db_manager

        db = get_db_manager()
        async with db.session() as session:
            # Check case_intake_progress table
            stmt = text(
                """
                SELECT user_id, case_id, current_block, current_step,
                       completed_blocks, updated_at
                FROM mega_agent.case_intake_progress
                WHERE case_id = :case_id AND user_id = :user_id
            """
            )
            result = await session.execute(stmt, {"case_id": CASE_ID, "user_id": USER_ID})
            row = result.fetchone()

            if row:
                print("✅ Raw database record:")
                print(f"   User ID: {row[0]}")
                print(f"   Case ID: {row[1]}")
                print(f"   Current block: {row[2]}")
                print(f"   Current step: {row[3]}")
                print(f"   Completed blocks: {row[4]}")
                print(f"   Updated at: {row[5]}")
            else:
                print("⚠️  No database record found")
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        import traceback

        traceback.print_exc()
    print()

    print("=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

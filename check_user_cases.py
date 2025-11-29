#!/usr/bin/env python3
"""Check all cases for a specific user."""
from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import text

from core.groupagents.case_agent import CaseAgent
from core.storage.connection import get_db_manager

USER_ID = "7314014306"  # Your Telegram user ID


async def main():
    """Check all cases for user."""
    print("=" * 80)
    print("USER CASES CHECK")
    print(f"User ID: {USER_ID}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 80)
    print()

    # Method 1: Using CaseAgent
    print("1. CASES VIA CASEAGENT")
    print("-" * 80)
    try:
        case_agent = CaseAgent()
        cases = await case_agent.alist_cases(client_id=USER_ID, limit=50)

        if cases:
            print(f"✅ Found {len(cases)} cases:")
            for idx, case in enumerate(cases, 1):
                print(f"\n   Case {idx}:")
                print(f"   ID: {case.id}")
                print(f"   Title: {case.title}")
                print(f"   Status: {case.status}")
                print(f"   Type: {case.case_type}")
                print(f"   Created: {case.created_at}")
                print(f"   Updated: {case.updated_at}")
        else:
            print(f"⚠️  No cases found for user {USER_ID}")
    except Exception as e:
        print(f"❌ Error fetching cases: {e}")
        import traceback

        traceback.print_exc()
    print()

    # Method 2: Direct SQL query
    print("2. CASES VIA DIRECT SQL")
    print("-" * 80)
    try:
        db = get_db_manager()
        async with db.session() as session:
            # Check cases table
            stmt = text(
                """
                SELECT id, title, status, case_type, client_id, created_at, updated_at
                FROM mega_agent.cases
                WHERE client_id = :user_id
                ORDER BY created_at DESC
                LIMIT 50
            """
            )
            result = await session.execute(stmt, {"user_id": USER_ID})
            rows = result.fetchall()

            if rows:
                print(f"✅ Found {len(rows)} cases in database:")
                for idx, row in enumerate(rows, 1):
                    print(f"\n   Case {idx}:")
                    print(f"   ID: {row[0]}")
                    print(f"   Title: {row[1]}")
                    print(f"   Status: {row[2]}")
                    print(f"   Type: {row[3]}")
                    print(f"   Client ID: {row[4]}")
                    print(f"   Created: {row[5]}")
                    print(f"   Updated: {row[6]}")
            else:
                print(f"⚠️  No cases in database for user {USER_ID}")
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        import traceback

        traceback.print_exc()
    print()

    # Method 3: Check intake progress table
    print("3. INTAKE PROGRESS RECORDS")
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
            rows = result.fetchall()

            if rows:
                print(f"✅ Found {len(rows)} intake progress records:")
                for idx, row in enumerate(rows, 1):
                    print(f"\n   Record {idx}:")
                    print(f"   User ID: {row[0]}")
                    print(f"   Case ID: {row[1]}")
                    print(f"   Current block: {row[2]}")
                    print(f"   Current step: {row[3]}")
                    print(f"   Completed blocks: {row[4]}")
                    print(f"   Updated: {row[5]}")
            else:
                print(f"⚠️  No intake progress records for user {USER_ID}")
    except Exception as e:
        print(f"❌ Error querying intake progress: {e}")
        import traceback

        traceback.print_exc()
    print()

    print("=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

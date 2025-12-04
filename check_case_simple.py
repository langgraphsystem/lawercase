"""
Simple case check that can run on Railway.
Uses environment variables directly.
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

CASE_ID = "6139bc5d-351c-4696-a80f-0dd34d15654e"
USER_ID = "7314014306"


async def check_case():
    """Check case data."""
    postgres_dsn = os.getenv("POSTGRES_DSN")
    if not postgres_dsn:
        print("❌ POSTGRES_DSN not set")
        return

    print("Connecting to database...")
    engine = create_async_engine(postgres_dsn, echo=False)

    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSession() as session:
        # Check case
        print(f"\n1️⃣  Checking case: {CASE_ID}")
        result = await session.execute(
            text(
                """
                SELECT case_id, user_id, title, status, case_type, created_at
                FROM mega_agent.cases
                WHERE case_id::text = :case_id
            """
            ),
            {"case_id": CASE_ID},
        )
        case = result.fetchone()

        if case:
            print("   ✅ FOUND!")
            print(f"      Title: {case[2]}")
            print(f"      Status: {case[3]}")
            print(f"      Type: {case[4]}")
            print(f"      Created: {case[5]}")
        else:
            print("   ❌ NOT FOUND")

        # Check intake progress
        print(f"\n2️⃣  Checking intake progress for case: {CASE_ID}")
        result = await session.execute(
            text(
                """
                SELECT current_block, current_step, completed_blocks, updated_at
                FROM mega_agent.case_intake_progress
                WHERE case_id = :case_id
            """
            ),
            {"case_id": CASE_ID},
        )
        progress = result.fetchone()

        if progress:
            print("   ✅ FOUND!")
            print(f"      Current block: {progress[0]}")
            print(f"      Current step: {progress[1]}")
            print(f"      Completed blocks: {progress[2]}")
            print(f"      Updated: {progress[3]}")
        else:
            print("   ❌ NOT FOUND")

        # Check semantic memory
        print(f"\n3️⃣  Checking semantic memory for case: {CASE_ID}")
        result = await session.execute(
            text(
                """
                SELECT COUNT(*) as count
                FROM mega_agent.semantic_memory
                WHERE metadata_json->>'case_id' = :case_id
            """
            ),
            {"case_id": CASE_ID},
        )
        count = result.scalar()

        print(f"   Records found: {count}")

        if count > 0:
            # Get sample records
            result = await session.execute(
                text(
                    """
                    SELECT text, metadata_json->>'question_id' as question_id, created_at
                    FROM mega_agent.semantic_memory
                    WHERE metadata_json->>'case_id' = :case_id
                    ORDER BY created_at ASC
                    LIMIT 5
                """
                ),
                {"case_id": CASE_ID},
            )
            records = result.fetchall()

            print("\n   Sample records:")
            for i, rec in enumerate(records, 1):
                answer_text = rec[0][:60] + "..." if len(rec[0]) > 60 else rec[0]
                print(f"      {i}. {answer_text}")
                print(f"         Question: {rec[1]}")
                print(f"         Created: {rec[2]}")
        else:
            print("   ⚠️  NO ANSWERS SAVED!")

        # Summary
        print(f"\n{'=' * 60}")
        print(f"SUMMARY FOR CASE {CASE_ID}")
        print(f"{'=' * 60}")
        print(f"Case exists: {'✅ YES' if case else '❌ NO'}")
        print(f"Intake progress: {'✅ YES' if progress else '❌ NO'}")
        print(f"Saved answers: {count} record(s)")

        if progress and count == 0:
            print("\n⚠️  WARNING: Intake in progress but NO answers saved!")
            print("            This indicates the in-memory storage bug.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_case())

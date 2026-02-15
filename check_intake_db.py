"""Check intake progress in database."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))


async def check_intake():
    """Query database for intake progress."""
    try:
        import asyncpg
    except ImportError:
        print("Installing asyncpg...")
        os.system("pip install asyncpg -q")  # noqa: S605, S607  # nosec B605 B607
        import asyncpg

    case_id = "20beeba5-976d-46ad-a627-309acdc0ab25"

    # Connection details from .env - using pooler with statement_cache_size=0
    conn = await asyncpg.connect(
        host=os.environ.get("DB_HOST", "aws-1-us-east-1.pooler.supabase.com"),
        port=int(os.environ.get("DB_PORT", "6543")),
        user=os.environ.get("DB_USER", "postgres.whcapsehbgreeumpfnil"),
        password=os.environ["DB_POSTGRES_PASSWORD"],
        database=os.environ.get("DB_NAME", "postgres"),
        ssl="require",
        statement_cache_size=0,
    )

    print("=" * 50)
    print("INTAKE PROGRESS CHECK")
    print("=" * 50)
    print(f"Case ID: {case_id}")
    print()

    # 1. Check case_intake_progress
    print("1. CASE INTAKE PROGRESS TABLE:")
    print("-" * 40)
    progress = await conn.fetch(
        "SELECT * FROM mega_agent.case_intake_progress WHERE case_id = $1", case_id
    )
    if progress:
        for row in progress:
            print(f"  User ID: {row['user_id']}")
            print(f"  Current Block: {row['current_block']}")
            print(f"  Current Step: {row['current_step']}")
            print(f"  Completed Blocks: {row['completed_blocks']}")
            print(f"  Updated At: {row.get('updated_at', 'N/A')}")
    else:
        print("  No intake progress found for this case")
    print()

    # 2. Check cases table
    print("2. CASES TABLE:")
    print("-" * 40)
    cases = await conn.fetch(
        "SELECT case_id, title, status, created_at, updated_at FROM mega_agent.cases WHERE case_id::text = $1",
        case_id,
    )
    if cases:
        for row in cases:
            print(f"  Case ID: {row['case_id']}")
            print(f"  Title: {row['title']}")
            print(f"  Status: {row['status']}")
            print(f"  Created: {row['created_at']}")
            print(f"  Updated: {row['updated_at']}")
    else:
        print("  Case not found in database")
    print()

    # 3. Check semantic_memory for intake answers
    print("3. SEMANTIC MEMORY (Intake Answers):")
    print("-" * 40)
    memories = await conn.fetch(
        """SELECT record_id, text, tags, type, source, created_at
           FROM mega_agent.semantic_memory
           WHERE case_id = $1
           ORDER BY created_at DESC
           LIMIT 20""",
        case_id,
    )
    if memories:
        for row in memories:
            print(f"  ID: {row['record_id']}")
            print(f"  Type: {row['type']} | Source: {row['source']}")
            text = row["text"]
            if len(text) > 100:
                text = text[:100] + "..."
            print(f"  Text: {text}")
            print(f"  Tags: {row['tags']}")
            print(f"  Created: {row['created_at']}")
            print()
    else:
        print("  No memories found for case_id column")
        # Try searching by tags
        memories = await conn.fetch(
            """SELECT record_id, text, tags, type, case_id, created_at
               FROM mega_agent.semantic_memory
               WHERE 'intake' = ANY(tags)
               ORDER BY created_at DESC
               LIMIT 10"""
        )
        if memories:
            print("  Found intake-tagged memories:")
            for row in memories:
                print(f"    Case: {row['case_id']} | Type: {row['type']}")
                text = row["text"][:80] + "..." if len(row["text"]) > 80 else row["text"]
                print(f"    Text: {text}")
                print()
        else:
            print("  No intake memories found")

    await conn.close()
    print("=" * 50)
    print("CHECK COMPLETE")


if __name__ == "__main__":
    asyncio.run(check_intake())

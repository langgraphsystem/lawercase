"""
Check semantic_memory using asyncpg directly.
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def check_memory():
    import asyncpg

    dsn = os.getenv("POSTGRES_DSN", "")
    if not dsn:
        print("❌ POSTGRES_DSN not set")
        return

    # Convert asyncpg URL format
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    case_id = "bf14054f-8d24-4ca6-be3e-ab5a8d295a73"
    user_id = "7314014306"

    print(f"Case ID: {case_id}")
    print(f"User ID: {user_id}")
    print("-" * 60)

    try:
        conn = await asyncpg.connect(dsn)
        print("✅ Connected to database")

        # Query semantic_memory for documents
        print("\n📝 Checking semantic_memory for documents...")
        rows = await conn.fetch(
            """
            SELECT
                record_id,
                text,
                type,
                tags,
                source,
                metadata_json,
                created_at
            FROM mega_agent.semantic_memory
            WHERE user_id = $1
            AND metadata_json->>'source' = 'smart_document_upload'
            ORDER BY created_at DESC
            LIMIT 10
            """,
            user_id,
        )

        if rows:
            print(f"   Found {len(rows)} document uploads")
            for row in rows:
                meta = row["metadata_json"] or {}
                print(f"\n   --- {str(row['record_id'])[:8]} ---")
                print(f"   📄 Type: {meta.get('document_type_name', 'N/A')}")
                print(f"   🔗 Linked to: {meta.get('linked_question_id', 'N/A')}")
                print(
                    f"   📋 Case: {meta.get('case_id', 'N/A')[:8] if meta.get('case_id') else 'N/A'}..."
                )
                print(f"   💾 Storage: {meta.get('storage_path', 'N/A')[:50]}...")
                print(f"   📅 Created: {row['created_at']}")
        else:
            print("   No document uploads found")

        # Check case in cases table
        print("\n📋 Checking cases table...")
        case_row = await conn.fetchrow(
            "SELECT * FROM mega_agent.cases WHERE case_id = $1",
            case_id,
        )
        if case_row:
            print(f"   ✅ Case exists: {case_row.get('title', 'N/A')}")
            print(f"   Status: {case_row.get('status', 'N/A')}")
        else:
            print("   ⚠️ Case not found in cases table")

        await conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_memory())

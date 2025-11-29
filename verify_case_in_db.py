"""
Direct database verification for case 6139bc5d-351c-4696-a80f-0dd34d15654e
Uses psycopg2 for synchronous connection to avoid async issues.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

CASE_ID = "6139bc5d-351c-4696-a80f-0dd34d15654e"

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 not installed. Installing...")
    import subprocess

    subprocess.check_call(["pip", "install", "-q", "psycopg2-binary"])
    import psycopg2
    from psycopg2.extras import RealDictCursor

# Get DB URL from environment
DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("SUPABASE_DB_URL or DATABASE_URL environment variable is required")


def check_database():
    """Check case data in database."""

    # Use DB URL from environment
    db_url = DB_URL

    print("=" * 80)
    print(f"DATABASE VERIFICATION FOR CASE: {CASE_ID}")
    print("=" * 80)
    print("\nConnecting to database...")
    print("Host: aws-1-us-east-1.pooler.supabase.com:6543")

    # Connect to database
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Check case
        print("\n1️⃣  CASE RECORD")
        print("-" * 80)
        cursor.execute(
            """
            SELECT case_id, user_id, title, status, case_type, created_at, updated_at
            FROM mega_agent.cases
            WHERE case_id::text = %s
        """,
            (CASE_ID,),
        )

        case = cursor.fetchone()

        if case:
            print("✅ Case found in database!")
            print(f"   Case ID: {case['case_id']}")
            print(f"   User ID: {case['user_id']}")
            print(f"   Title: {case['title']}")
            print(f"   Status: {case['status']}")
            print(f"   Type: {case['case_type']}")
            print(f"   Created: {case['created_at']}")
            print(f"   Updated: {case['updated_at']}")
        else:
            print("❌ Case NOT found in database!")
            return

        # 2. Check intake progress
        print("\n2️⃣  INTAKE PROGRESS")
        print("-" * 80)
        cursor.execute(
            """
            SELECT user_id, case_id, current_block, current_step,
                   completed_blocks, updated_at
            FROM mega_agent.case_intake_progress
            WHERE case_id = %s
        """,
            (CASE_ID,),
        )

        progress = cursor.fetchone()

        if progress:
            print("✅ Intake progress found!")
            print(f"   Case ID: {progress['case_id']}")
            print(f"   Current Block: {progress['current_block']}")
            print(f"   Current Step: {progress['current_step']}")

            completed = progress["completed_blocks"] or []
            print(f"   Completed Blocks: {completed}")
            print(f"   Updated: {progress['updated_at']}")

            if completed:
                print(f"\n   📋 Completed Blocks ({len(completed)}):")
                for i, block in enumerate(completed, 1):
                    print(f"      {i}. {block}")
        else:
            print("ℹ️  No intake progress found")

        # 3. Check semantic memory (intake answers)
        print("\n3️⃣  SEMANTIC MEMORY (Intake Answers)")
        print("-" * 80)
        cursor.execute(
            """
            SELECT record_id, user_id, text, tags, metadata_json, created_at
            FROM mega_agent.semantic_memory
            WHERE metadata_json->>'case_id' = %s
            ORDER BY created_at ASC
        """,
            (CASE_ID,),
        )

        memories = cursor.fetchall()

        if memories:
            print(f"✅ Found {len(memories)} semantic memory records in database!")
            print()

            for i, mem in enumerate(memories, 1):
                print(f"   📝 Answer #{i}")
                print(f"   ├─ Record ID: {mem['record_id']}")

                text = mem["text"]
                print(f"   ├─ Text: {text[:80]}..." if len(text) > 80 else f"   ├─ Text: {text}")
                print(f"   ├─ Tags: {mem['tags']}")

                metadata = mem["metadata_json"] or {}
                if metadata:
                    print("   ├─ Metadata:")
                    print(f"   │  ├─ source: {metadata.get('source')}")
                    print(f"   │  ├─ question_id: {metadata.get('question_id')}")
                    print(f"   │  ├─ case_id: {metadata.get('case_id')}")
                    if "raw_response" in metadata:
                        raw = metadata["raw_response"]
                        print(
                            f"   │  └─ raw_response: {raw[:60]}..."
                            if len(raw) > 60
                            else f"   │  └─ raw_response: {raw}"
                        )

                print(f"   └─ Created: {mem['created_at']}")
                print()
        else:
            print("❌ NO semantic memory records found in database!")
            print("   ⚠️  This would indicate data loss, but logs show saves...")

        # 4. Summary
        print("=" * 80)
        print("DATABASE VERIFICATION SUMMARY")
        print("=" * 80)

        case_status = "✅ EXISTS" if case else "❌ MISSING"
        progress_status = "✅ EXISTS" if progress else "❌ MISSING"
        memory_count = len(memories) if memories else 0
        memory_status = f"✅ {memory_count} records" if memory_count > 0 else "❌ 0 records"

        print(f"Case Record:        {case_status}")
        print(f"Intake Progress:    {progress_status}")
        print(f"Semantic Memory:    {memory_status}")
        print("Expected from logs: 6 answers (full_name, date_of_birth, place_of_birth,")
        print("                                citizenship, current_residence, main_field)")

        if memory_count == 6:
            print("\n🎉 PERFECT! All 6 answers are saved in database!")
        elif memory_count > 0:
            print(f"\n⚠️  WARNING: Found {memory_count} answers, expected 6")
        else:
            print("\n❌ CRITICAL: No answers in database despite logs showing saves!")

        print()

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    try:
        check_database()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

"""
List all cases for user 7314014306 from mega_agent schema.
"""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_ID = "7314014306"


def supabase_query(table, filters=None, select="*", order=None):
    """Query Supabase REST API with mega_agent schema."""
    # Use schema prefix for tables
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"

    if filters:
        for key, value in filters.items():
            url += f"&{key}=eq.{value}"

    if order:
        url += f"&order={order}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept-Profile": "mega_agent",  # Specify schema
        "Content-Profile": "mega_agent",  # Specify schema
    }

    req = Request(url, headers=headers)

    try:
        with urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error querying {table}: {e}")
        return []


def main():
    print("=" * 80)
    print(f"ALL CASES FOR USER: {USER_ID} (mega_agent schema)")
    print("=" * 80)
    print()

    # Get all cases
    cases = supabase_query("cases", filters={"user_id": USER_ID}, order="created_at.desc")

    if cases:
        print(f"✅ Found {len(cases)} case(s)!")
        print()

        for i, case in enumerate(cases, 1):
            print(f"📋 Case #{i}")
            print(f"   ├─ Case ID: {case.get('case_id')}")
            print(f"   ├─ Title: {case.get('title')}")
            print(f"   ├─ Status: {case.get('status')}")
            print(f"   ├─ Type: {case.get('case_type')}")
            print(f"   ├─ Created: {case.get('created_at')}")
            print(f"   └─ Updated: {case.get('updated_at')}")
            print()
    else:
        print(f"ℹ️  No cases found for user {USER_ID}")

    print()

    # Get all intake progress
    print("=" * 80)
    print("INTAKE PROGRESS RECORDS")
    print("=" * 80)
    print()

    progress_list = supabase_query(
        "case_intake_progress", filters={"user_id": USER_ID}, order="updated_at.desc"
    )

    if progress_list:
        print(f"✅ Found {len(progress_list)} intake progress record(s)!")
        print()

        for i, progress in enumerate(progress_list, 1):
            print(f"📝 Progress #{i}")
            print(f"   ├─ Case ID: {progress.get('case_id')}")
            print(f"   ├─ Current Block: {progress.get('current_block')}")
            print(f"   ├─ Current Step: {progress.get('current_step')}")
            completed = progress.get("completed_blocks") or []
            print(f"   ├─ Completed Blocks ({len(completed)}): {completed}")
            print(f"   └─ Updated: {progress.get('updated_at')}")
            print()
    else:
        print("ℹ️  No intake progress records found")

    print()

    # Check semantic memory
    print("=" * 80)
    print("SEMANTIC MEMORY RECORDS")
    print("=" * 80)
    print()

    memories = supabase_query(
        "semantic_memory", filters={"user_id": USER_ID}, order="created_at.desc"
    )

    if memories:
        print(f"✅ Found {len(memories)} semantic memory record(s)!")
        print()

        for i, mem in enumerate(memories[:10], 1):  # Show first 10
            print(f"💭 Memory #{i}")
            text = mem.get("text", "")
            print(f"   ├─ Text: {text[:80]}..." if len(text) > 80 else f"   ├─ Text: {text}")
            print(f"   ├─ Tags: {mem.get('tags')}")

            metadata = mem.get("metadata_json", {})
            if metadata:
                case_id = metadata.get("case_id")
                question_id = metadata.get("question_id")
                if case_id:
                    print(f"   ├─ Case ID: {case_id}")
                if question_id:
                    print(f"   ├─ Question: {question_id}")

            print(f"   └─ Created: {mem.get('created_at')}")
            print()

        if len(memories) > 10:
            print(f"   ... and {len(memories) - 10} more records")
    else:
        print("ℹ️  No semantic memory records found")

    print()


if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        exit(1)

    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)

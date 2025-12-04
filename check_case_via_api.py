"""
Check specific case data via Supabase REST API.
"""

from __future__ import annotations

import json
import os
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CASE_ID = "6139bc5d-351c-4696-a80f-0dd34d15654e"


def supabase_query(table, filters=None, select="*", order=None):
    """Query Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"

    if filters:
        for key, value in filters.items():
            url += f"&{key}=eq.{quote(str(value))}"

    if order:
        url += f"&order={order}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
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
    print(f"CHECKING CASE DATA: {CASE_ID}")
    print("=" * 80)
    print()

    # 1. Check case
    print("1️⃣  CASE RECORD")
    print("-" * 80)
    cases = supabase_query("cases", filters={"case_id": CASE_ID})

    if cases:
        case = cases[0]
        print("✅ Case found!")
        print(f"   Case ID: {case.get('case_id')}")
        print(f"   User ID: {case.get('user_id')}")
        print(f"   Title: {case.get('title')}")
        print(f"   Status: {case.get('status')}")
        print(f"   Type: {case.get('case_type')}")
        print(f"   Created: {case.get('created_at')}")
        print(f"   Updated: {case.get('updated_at')}")
        user_id = case.get("user_id")
    else:
        print("❌ Case NOT found!")
        return

    print()

    # 2. Check intake progress
    print("2️⃣  INTAKE PROGRESS")
    print("-" * 80)
    progress_list = supabase_query("case_intake_progress", filters={"case_id": CASE_ID})

    if progress_list:
        progress = progress_list[0]
        print("✅ Intake progress found!")
        print(f"   User ID: {progress.get('user_id')}")
        print(f"   Case ID: {progress.get('case_id')}")
        print(f"   Current Block: {progress.get('current_block')}")
        print(f"   Current Step: {progress.get('current_step')}")

        completed_blocks = progress.get("completed_blocks") or []
        print(f"   Completed Blocks: {completed_blocks}")
        print(f"   Updated: {progress.get('updated_at')}")

        if completed_blocks:
            print(f"\n   📋 Completed Blocks ({len(completed_blocks)}):")
            for i, block in enumerate(completed_blocks, 1):
                print(f"      {i}. {block}")
    else:
        print("❌ Intake progress NOT found!")

    print()

    # 3. Check semantic memory
    print("3️⃣  SEMANTIC MEMORY (Intake Answers)")
    print("-" * 80)

    # We need to filter by metadata_json->case_id
    # Supabase PostgREST syntax for JSONB: metadata_json->>case_id
    memories = supabase_query(
        "semantic_memory",
        filters={},  # Can't easily filter JSONB in REST API, will filter client-side
        order="created_at.asc",
    )

    # Filter client-side for case_id in metadata
    case_memories = [m for m in memories if m.get("metadata_json", {}).get("case_id") == CASE_ID]

    if case_memories:
        print(f"✅ Found {len(case_memories)} semantic memory records!")
        print()
        for i, mem in enumerate(case_memories, 1):
            print(f"   Record #{i}")
            print(f"   ├─ ID: {mem.get('record_id')}")
            print(f"   ├─ User ID: {mem.get('user_id')}")

            text = mem.get("text", "")
            print(f"   ├─ Text: {text[:100]}..." if len(text) > 100 else f"   ├─ Text: {text}")
            print(f"   ├─ Tags: {mem.get('tags')}")

            metadata = mem.get("metadata_json", {})
            if metadata:
                print("   ├─ Metadata:")
                print(f"   │  ├─ source: {metadata.get('source')}")
                print(f"   │  ├─ question_id: {metadata.get('question_id')}")
                print(f"   │  ├─ case_id: {metadata.get('case_id')}")
                if "raw_response" in metadata:
                    raw = metadata["raw_response"]
                    print(
                        f"   │  └─ raw_response: {raw[:50]}..."
                        if len(raw) > 50
                        else f"   │  └─ raw_response: {raw}"
                    )

            print(f"   └─ Created: {mem.get('created_at')}")
            print()
    else:
        print("❌ NO semantic memory records found!")
        print("   ⚠️  This means intake answers were NOT saved!")

    print()

    # 4. Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    case_status = "✅ EXISTS" if cases else "❌ MISSING"
    progress_status = "✅ EXISTS" if progress_list else "❌ MISSING"
    memory_count = len(case_memories)
    memory_status = (
        f"✅ {memory_count} records" if memory_count > 0 else "❌ 0 records (DATA LOSS!)"
    )

    print(f"Case Record:      {case_status}")
    print(f"Intake Progress:  {progress_status}")
    print(f"Semantic Memory:  {memory_status}")

    if progress_list and case_memories:
        completed_count = len(progress_list[0].get("completed_blocks") or [])
        print()
        print("📊 Data Integrity Check:")
        print(f"   Completed Blocks: {completed_count}")
        print(f"   Saved Answers: {memory_count}")

        if memory_count > 0:
            print("\n   ✅ SUCCESS: Answers are being saved to database!")
        else:
            print("\n   ❌ CRITICAL: Answers are NOT saved (in-memory storage bug)")

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

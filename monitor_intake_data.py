#!/usr/bin/env python3
"""Real-time monitoring of intake data in Supabase tables."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
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
    """Monitor intake data in Supabase."""
    print_header("SUPABASE INTAKE DATA MONITOR")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"User ID: {USER_ID}")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n❌ ERROR: Missing Supabase credentials in .env file")
        print("   Required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")
        return

    # Create Supabase client with custom schema
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Note: Supabase PostgREST uses 'public' schema by default
    # For custom schemas like 'mega_agent', we need to use schema parameter
    # However, the Python client doesn't directly support this,
    # so we'll need to check if tables are exposed via PostgREST

    # 1. Check intake progress
    print_subheader("1. INTAKE PROGRESS RECORDS")
    try:
        # Try to access table with schema prefix
        response = (
            supabase.schema("mega_agent")
            .table("case_intake_progress")
            .select("*")
            .eq("user_id", USER_ID)
            .execute()
        )

        if response.data:
            print(f"✅ Found {len(response.data)} intake progress record(s):\n")
            for idx, record in enumerate(response.data, 1):
                print(f"Record {idx}:")
                print(f"  ├─ Case ID: {record.get('case_id')}")
                print(f"  ├─ Current Block: {record.get('current_block')}")
                print(f"  ├─ Current Step: {record.get('current_step')}")
                print(f"  ├─ Completed Blocks: {record.get('completed_blocks')}")
                print(f"  └─ Updated: {record.get('updated_at')}")
                print()
        else:
            print("⚠️  No intake progress records found")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 2. Check cases
    print_subheader("2. CASE RECORDS")
    try:
        response = (
            supabase.schema("mega_agent")
            .table("cases")
            .select("*")
            .eq("user_id", USER_ID)
            .execute()
        )

        if response.data:
            print(f"✅ Found {len(response.data)} case(s):\n")
            for idx, case in enumerate(response.data, 1):
                print(f"Case {idx}:")
                print(f"  ├─ Case ID: {case.get('case_id')}")
                print(f"  ├─ Title: {case.get('title')}")
                print(f"  ├─ Status: {case.get('status')}")
                print(f"  ├─ Type: {case.get('case_type')}")
                print(f"  ├─ Created: {case.get('created_at')}")
                print(f"  └─ Updated: {case.get('updated_at')}")
                print()
        else:
            print("⚠️  No cases found")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 3. Check semantic memory (intake answers)
    print_subheader("3. SEMANTIC MEMORY (Intake Answers)")
    try:
        response = (
            supabase.schema("mega_agent")
            .table("semantic_memory")
            .select("*")
            .eq("user_id", USER_ID)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )

        if response.data:
            print(f"✅ Found {len(response.data)} semantic memory record(s):\n")

            # Group by tags
            intake_records = [r for r in response.data if "intake" in str(r.get("tags", []))]

            if intake_records:
                print(f"📝 Intake-related records: {len(intake_records)}\n")
                for idx, record in enumerate(intake_records[:10], 1):
                    text = record.get("text", "")
                    tags = record.get("tags", [])
                    metadata = record.get("metadata_json", {})

                    print(f"  Record {idx}:")
                    print(f"  ├─ Text: {text[:100]}{'...' if len(text) > 100 else ''}")
                    print(f"  ├─ Tags: {tags}")
                    print(f"  ├─ Question ID: {metadata.get('question_id', 'N/A')}")
                    print(f"  └─ Created: {record.get('created_at')}")
                    print()
            else:
                print("⚠️  No intake-tagged records found")
        else:
            print("⚠️  No semantic memory records found")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 4. Check episodic memory (events)
    print_subheader("4. EPISODIC MEMORY (Recent Events)")
    try:
        response = (
            supabase.schema("mega_agent")
            .table("episodic_memory")
            .select("*")
            .eq("user_id", USER_ID)
            .order("timestamp", desc=True)
            .limit(10)
            .execute()
        )

        if response.data:
            print(f"✅ Found {len(response.data)} recent event(s):\n")
            for idx, event in enumerate(response.data, 1):
                print(f"  Event {idx}:")
                print(f"  ├─ Source: {event.get('source')}")
                print(f"  ├─ Action: {event.get('action')}")
                payload = str(event.get("payload", ""))
                print(f"  ├─ Payload: {payload[:80]}{'...' if len(payload) > 80 else ''}")
                print(f"  └─ Timestamp: {event.get('timestamp')}")
                print()
        else:
            print("⚠️  No episodic events found")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 5. Real-time summary
    print_header("SUMMARY")
    try:
        # Count records
        progress_count = len(
            supabase.schema("mega_agent")
            .table("case_intake_progress")
            .select("*")
            .eq("user_id", USER_ID)
            .execute()
            .data
        )
        cases_count = len(
            supabase.schema("mega_agent")
            .table("cases")
            .select("*")
            .eq("user_id", USER_ID)
            .execute()
            .data
        )
        semantic_count = len(
            supabase.schema("mega_agent")
            .table("semantic_memory")
            .select("*")
            .eq("user_id", USER_ID)
            .execute()
            .data
        )
        episodic_count = len(
            supabase.schema("mega_agent")
            .table("episodic_memory")
            .select("*")
            .eq("user_id", USER_ID)
            .execute()
            .data
        )

        print("\n📊 Data Overview:")
        print(f"  ├─ Intake Progress Records: {progress_count}")
        print(f"  ├─ Cases: {cases_count}")
        print(f"  ├─ Semantic Memory Records: {semantic_count}")
        print(f"  └─ Episodic Events: {episodic_count}")

        print("\n✅ Monitoring complete!")

        # Show specific advice
        if progress_count > 0 and semantic_count == 0:
            print("\n⚠️  WARNING: Intake progress exists but no semantic memory records found!")
            print("   This may indicate that answers are NOT being saved to semantic memory.")

    except Exception as e:
        print(f"❌ Error in summary: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

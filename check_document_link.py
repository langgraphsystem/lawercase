"""
Check where a document was linked in the database.
Uses Supabase SQL API directly.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
import httpx

load_dotenv()


def check_document_link(
    case_id: str = "bf14054f-8d24-4ca6-be3e-ab5a8d295a73",
    user_id: str = "7314014306",
):
    """Check document links in semantic_memory via SQL API."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        return

    print(f"Case ID: {case_id}")
    print(f"User ID: {user_id}")
    print("-" * 60)

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }

    # Use Supabase SQL API (via RPC)
    rpc_url = f"{supabase_url}/rest/v1/rpc/exec_sql"

    # Query semantic_memory for this case
    sql_query = f"""
    SELECT
        record_id,
        text,
        type,
        tags,
        source,
        metadata_json,
        created_at
    FROM mega_agent.semantic_memory
    WHERE user_id = '{user_id}'
    AND (
        metadata_json->>'case_id' = '{case_id}'
        OR metadata_json->>'source' = 'smart_document_upload'
    )
    ORDER BY created_at DESC
    LIMIT 20
    """

    with httpx.Client(timeout=30) as client:
        # Try direct SQL via pg_graphql or check if there's an RPC function
        # First, let's try the simpler approach - query via view if exists

        # Check cases table first
        print("\n📋 Checking cases table...")
        cases_url = f"{supabase_url}/rest/v1/cases"
        resp = client.get(
            cases_url,
            headers={**headers, "Accept-Profile": "mega_agent"},
            params={"case_id": f"eq.{case_id}", "select": "*"},
        )
        if resp.status_code == 200:
            cases = resp.json()
            if cases:
                print(f"   ✅ Case found: {cases[0].get('title', 'N/A')}")
                print(f"   Status: {cases[0].get('status', 'N/A')}")
                print(f"   Created: {cases[0].get('created_at', 'N/A')}")
            else:
                print("   ⚠️ Case not found in cases table")
        else:
            print(f"   Cannot query cases: {resp.status_code}")

        # Check semantic_memory
        print("\n📝 Checking semantic_memory...")
        semantic_url = f"{supabase_url}/rest/v1/semantic_memory"
        resp = client.get(
            semantic_url,
            headers={**headers, "Accept-Profile": "mega_agent"},
            params={
                "user_id": f"eq.{user_id}",
                "select": "record_id,text,type,tags,source,metadata_json,created_at",
                "order": "created_at.desc",
                "limit": "20",
            },
        )
        if resp.status_code == 200:
            records = resp.json()
            if records:
                print(f"   Found {len(records)} memory records for user")

                # Filter for documents
                doc_records = [
                    r
                    for r in records
                    if r.get("metadata_json", {}).get("source") == "smart_document_upload"
                    or "document" in str(r.get("tags", []))
                ]

                print(f"\n📄 Document records: {len(doc_records)}")
                for rec in doc_records:
                    meta = rec.get("metadata_json", {})
                    print(f"\n   --- Record {str(rec.get('record_id', ''))[:8]} ---")
                    print(f"   Type: {meta.get('document_type_name', 'N/A')}")
                    print(f"   Linked question: {meta.get('linked_question_id', 'N/A')}")
                    print(f"   Case ID: {meta.get('case_id', 'N/A')}")
                    print(f"   Storage path: {meta.get('storage_path', 'N/A')[:60]}...")
                    print(f"   Created: {rec.get('created_at', 'N/A')}")
                    text_preview = str(rec.get("text", ""))[:100]
                    print(f"   Text: {text_preview}...")
            else:
                print("   No memory records found")
        else:
            print(f"   Error: {resp.status_code} - {resp.text[:200]}")

        # Also check documents table
        print("\n📁 Checking documents table...")
        docs_url = f"{supabase_url}/rest/v1/documents"
        resp = client.get(
            docs_url,
            headers={**headers, "Accept-Profile": "mega_agent"},
            params={
                "case_id": f"eq.{case_id}",
                "select": "*",
            },
        )
        if resp.status_code == 200:
            docs = resp.json()
            if docs:
                print(f"   Found {len(docs)} documents")
                for doc in docs:
                    print(f"   - {doc.get('document_type', 'N/A')}: {doc.get('file_name', 'N/A')}")
            else:
                print("   No documents in documents table")
        else:
            print(f"   Error: {resp.status_code}")


if __name__ == "__main__":
    import sys

    case_id = sys.argv[1] if len(sys.argv) > 1 else "bf14054f-8d24-4ca6-be3e-ab5a8d295a73"
    user_id = sys.argv[2] if len(sys.argv) > 2 else "7314014306"
    check_document_link(case_id, user_id)

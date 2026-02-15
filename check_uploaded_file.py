"""
Verify that a document was actually uploaded to Supabase Storage.
Uses httpx directly to avoid websockets dependency issues.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
import httpx

load_dotenv()


def check_file_in_storage(
    user_id: str = "7314014306",
    case_id: str = "bf14054f-8d24-4ca6-be3e-ab5a8d295a73",
):
    """Check if files exist in Supabase storage for given user/case."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
        "SUPABASE_ANON_KEY", ""
    )

    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env")
        return

    print(f"Supabase URL: {supabase_url[:50]}...")
    print("Bucket: intake-documents")
    print(f"User ID: {user_id}")
    print(f"Case ID: {case_id}")
    print("-" * 60)

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    }

    # Headers for mega_agent schema
    schema_headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "mega_agent",  # For SELECT queries
    }

    bucket_name = "intake-documents"

    # List files in user's folder
    print(f"\n📁 Listing files for user {user_id}...")
    list_url = f"{supabase_url}/storage/v1/object/list/{bucket_name}"

    try:
        with httpx.Client(timeout=30) as client:
            # List user folder
            resp = client.post(
                list_url,
                headers=headers,
                json={"prefix": f"{user_id}/", "limit": 100},
            )
            if resp.status_code == 200:
                items = resp.json()
                if items:
                    print(f"   Found {len(items)} items in user folder")
                    for item in items[:10]:
                        name = item.get("name", "unknown")
                        print(f"   - {name}")
                else:
                    print("   ⚠️ No files found in user folder")
            else:
                print(f"   ❌ Error: {resp.status_code} - {resp.text[:200]}")

            # List case folder
            case_path = f"{user_id}/{case_id}"
            print(f"\n📁 Listing files in case folder: {case_path}...")
            resp = client.post(
                list_url,
                headers=headers,
                json={"prefix": f"{case_path}/", "limit": 100},
            )
            if resp.status_code == 200:
                items = resp.json()
                if items:
                    print(f"   ✅ Found {len(items)} files in case folder:")
                    for item in items:
                        name = item.get("name", "unknown")
                        size = item.get("metadata", {}).get("size", "?")
                        created = item.get("created_at", "?")
                        print(f"   - {name}")
                        print(f"     Size: {size} bytes, Created: {created}")

                        # Build public URL
                        full_path = f"{case_path}/{name}"
                        public_url = (
                            f"{supabase_url}/storage/v1/object/public/{bucket_name}/{full_path}"
                        )
                        print(f"     URL: {public_url[:100]}...")
                else:
                    print("   ⚠️ No files found in case folder")
            else:
                print(f"   ❌ Error: {resp.status_code} - {resp.text[:200]}")

            # Check intake_answers table (mega_agent schema)
            print(f"\n📝 Checking intake_answers for case {case_id[:8]}...")
            intake_url = f"{supabase_url}/rest/v1/intake_answers"
            resp = client.get(
                intake_url,
                headers=schema_headers,
                params={"case_id": f"eq.{case_id}", "select": "*"},
            )
            if resp.status_code == 200:
                records = resp.json()
                if records:
                    print(f"   Found {len(records)} intake answers")
                    for rec in records:
                        q_key = rec.get("question_key", "unknown")
                        q_text = rec.get("question_text", "")[:50]
                        answer = str(rec.get("answer_value", ""))[:80]
                        answer_data = rec.get("answer_data", {})
                        print(f"   - Question: {q_key}")
                        print(f"     Text: {q_text}...")
                        print(f"     Answer: {answer}...")
                        if answer_data:
                            print(f"     Data: {str(answer_data)[:100]}...")
                else:
                    print("   No intake answers found for this case")
            else:
                print(f"   Error querying intake_answers: {resp.status_code} - {resp.text[:100]}")

            # Check episodic_memory table (documents saved via smart upload)
            print(f"\n📝 Checking episodic_memory for case {case_id[:8]}...")
            episodic_url = f"{supabase_url}/rest/v1/episodic_memory"
            resp = client.get(
                episodic_url,
                headers=schema_headers,
                params={"case_id": f"eq.{case_id}", "select": "*"},
            )
            if resp.status_code == 200:
                records = resp.json()
                if records:
                    print(f"   Found {len(records)} episodic memory records")
                    for rec in records[:5]:
                        content = str(rec.get("content", ""))[:80]
                        metadata = rec.get("metadata", {})
                        doc_type = metadata.get("document_type", "unknown")
                        storage_path = metadata.get("storage_path", "")
                        linked_q = metadata.get("linked_question_id", "")
                        print(f"   - Type: {doc_type}")
                        if linked_q:
                            print(f"     Linked question: {linked_q}")
                        if storage_path:
                            print(f"     Storage path: {storage_path}")
                        print(f"     Content: {content}...")
                else:
                    print("   No episodic memory found for this case")
            else:
                print(f"   Error querying episodic_memory: {resp.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else "7314014306"
    case_id = sys.argv[2] if len(sys.argv) > 2 else "bf14054f-8d24-4ca6-be3e-ab5a8d295a73"

    check_file_in_storage(user_id, case_id)

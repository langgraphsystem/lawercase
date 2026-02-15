"""Check case in database."""

from __future__ import annotations

import os

from dotenv import load_dotenv
import psycopg2

load_dotenv()

DB_URL = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
db_url = (
    DB_URL.replace("postgresql+asyncpg://", "postgresql://") if "+asyncpg" in DB_URL else DB_URL
)

conn = psycopg2.connect(db_url)
cur = conn.cursor()

case_id = "bf14054f-8d24-4ca6-be3e-ab5a8d295a73"
user_id = "7314014306"

# Check cases table
print("=== CASES TABLE ===")
cur.execute(
    "SELECT case_id, user_id, title, status, created_at FROM mega_agent.cases WHERE case_id = %s",
    (case_id,),
)
row = cur.fetchone()
if row:
    print(f"Case ID: {row[0]}")
    print(f"User ID: {row[1]}")
    print(f"Title: {row[2]}")
    print(f"Status: {row[3]}")
    print(f"Created: {row[4]}")
else:
    print("Case NOT FOUND in cases table")

# Check intake progress
print("\n=== INTAKE PROGRESS ===")
cur.execute(
    "SELECT user_id, case_id, current_block, current_step, completed_blocks, updated_at FROM mega_agent.case_intake_progress WHERE case_id = %s",
    (case_id,),
)
row = cur.fetchone()
if row:
    print(f"User ID: {row[0]}")
    print(f"Case ID: {row[1]}")
    print(f"Current Block: {row[2]}")
    print(f"Current Step: {row[3]}")
    print(f"Completed Blocks: {row[4]}")
    print(f"Updated: {row[5]}")
else:
    print("No intake progress found")

# Check semantic memory
print("\n=== SEMANTIC MEMORY ===")
cur.execute(
    """SELECT record_id, text, type, tags, created_at
FROM mega_agent.semantic_memory
WHERE metadata_json->>'case_id' = %s
ORDER BY created_at DESC
LIMIT 10""",
    (case_id,),
)
rows = cur.fetchall()
print(f"Found {len(rows)} memory records")
for row in rows:
    print(f"  ID: {str(row[0])[:8]}...")
    print(f"  Type: {row[2]}")
    print(f"  Tags: {row[3]}")
    text = row[1][:100] + "..." if len(row[1]) > 100 else row[1]
    print(f"  Text: {text}")
    print("  ---")

# Check ALL semantic memory for this user
print("\n=== ALL SEMANTIC MEMORY FOR USER ===")
cur.execute(
    """SELECT record_id, text, type, tags, metadata_json, created_at
FROM mega_agent.semantic_memory
WHERE user_id = %s
ORDER BY created_at DESC
LIMIT 20""",
    (user_id,),
)
rows = cur.fetchall()
print(f"Found {len(rows)} memory records for user {user_id}")
for row in rows:
    print(f"  ID: {str(row[0])[:8]}")
    text = row[1][:80] + "..." if len(row[1]) > 80 else row[1]
    print(f"  Text: {text}")
    print(f"  Type: {row[2]}, Tags: {row[3]}")
    print(f"  Meta: {row[4]}")
    print("  ---")

# Check total count
cur.execute("SELECT COUNT(*) FROM mega_agent.semantic_memory")
total = cur.fetchone()[0]
print(f"\nTotal records in semantic_memory: {total}")

cur.close()
conn.close()

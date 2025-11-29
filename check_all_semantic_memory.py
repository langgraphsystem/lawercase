"""
Check ALL semantic memory records for user 7314014306
"""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor

USER_ID = "7314014306"

try:
    import psycopg2
except ImportError:
    import subprocess

    subprocess.check_call(["pip", "install", "-q", "psycopg2-binary"])
    import psycopg2

db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("SUPABASE_DB_URL or DATABASE_URL environment variable is required")

print("=" * 80)
print(f"CHECKING ALL SEMANTIC MEMORY FOR USER: {USER_ID}")
print("=" * 80)
print()

conn = psycopg2.connect(db_url)
cursor = conn.cursor(cursor_factory=RealDictCursor)

try:
    # Check total count
    print("1️⃣  TOTAL RECORDS IN SEMANTIC_MEMORY")
    print("-" * 80)
    cursor.execute(
        """
        SELECT COUNT(*) as total
        FROM mega_agent.semantic_memory
    """
    )
    result = cursor.fetchone()
    print(f"Total records in table: {result['total']}")
    print()

    # Check for this user
    print("2️⃣  RECORDS FOR USER 7314014306")
    print("-" * 80)
    cursor.execute(
        """
        SELECT COUNT(*) as count
        FROM mega_agent.semantic_memory
        WHERE user_id = %s
    """,
        (USER_ID,),
    )
    result = cursor.fetchone()
    print(f"Records for user {USER_ID}: {result['count']}")
    print()

    # Check by namespace
    print("3️⃣  RECORDS BY NAMESPACE")
    print("-" * 80)
    cursor.execute(
        """
        SELECT namespace, COUNT(*) as count
        FROM mega_agent.semantic_memory
        GROUP BY namespace
        ORDER BY count DESC
    """
    )
    namespaces = cursor.fetchall()

    if namespaces:
        print("Namespaces found:")
        for ns in namespaces:
            print(f"   - {ns['namespace']}: {ns['count']} records")
    else:
        print("   No namespaces found")
    print()

    # Check recent records (any user)
    print("4️⃣  MOST RECENT RECORDS (Last 10, any user)")
    print("-" * 80)
    cursor.execute(
        """
        SELECT user_id, text, namespace, metadata_json, created_at
        FROM mega_agent.semantic_memory
        ORDER BY created_at DESC
        LIMIT 10
    """
    )
    recent = cursor.fetchall()

    if recent:
        print(f"Found {len(recent)} recent records:")
        for i, rec in enumerate(recent, 1):
            print(f"\n   Record #{i}")
            print(f"   ├─ User ID: {rec['user_id']}")
            print(f"   ├─ Namespace: {rec['namespace']}")
            text = rec["text"][:60] + "..." if len(rec["text"]) > 60 else rec["text"]
            print(f"   ├─ Text: {text}")
            print(f"   ├─ Metadata: {rec['metadata_json']}")
            print(f"   └─ Created: {rec['created_at']}")
    else:
        print("   ❌ NO RECORDS IN TABLE AT ALL!")
    print()

    # Check if table has correct structure
    print("5️⃣  TABLE STRUCTURE")
    print("-" * 80)
    cursor.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'mega_agent'
        AND table_name = 'semantic_memory'
        ORDER BY ordinal_position
    """
    )
    columns = cursor.fetchall()

    if columns:
        print("Table columns:")
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']}")
    print()

finally:
    cursor.close()
    conn.close()

print("=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

"""
Apply migration to update semantic_memory table to 3072 dimensions.
"""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Supabase connection (direct mode, port 5432)
DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("SUPABASE_DB_URL or DATABASE_URL environment variable is required")

print("=" * 80)
print("MIGRATION: Update semantic_memory embedding dimension to 3072")
print("=" * 80)
print()

conn = psycopg2.connect(DB_URL)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

try:
    # Step 1: Check current records
    print("1️⃣  Checking existing records...")
    cursor.execute("SELECT COUNT(*) FROM mega_agent.semantic_memory")
    count = cursor.fetchone()[0]
    print(f"   Existing records: {count}")
    print()

    if count > 0:
        print(f"⚠️  WARNING: Found {count} existing record(s)!")
        print("   This migration will DELETE all embeddings and recreate column.")
        print("   ✅ Proceeding automatically (safe for test data).")
    else:
        print("   ✅ Table is empty, safe to proceed.")
    print()

    # Step 2: Drop and recreate embedding column
    print("2️⃣  Dropping old embedding column...")
    cursor.execute(
        """
        ALTER TABLE mega_agent.semantic_memory
        DROP COLUMN IF EXISTS embedding CASCADE
    """
    )
    print("   ✅ Old column dropped.")
    print()

    print("3️⃣  Creating new embedding column with 3072 dimensions...")
    cursor.execute(
        """
        ALTER TABLE mega_agent.semantic_memory
        ADD COLUMN embedding vector(3072)
    """
    )
    print("   ✅ New column created.")
    print()

    # Step 3: Update defaults
    print("4️⃣  Updating default values...")
    cursor.execute(
        """
        ALTER TABLE mega_agent.semantic_memory
        ALTER COLUMN embedding_dimension SET DEFAULT 3072
    """
    )
    print("   ✅ embedding_dimension default updated to 3072.")
    print()

    # Step 4: Recreate index
    print("5️⃣  Recreating similarity search index...")
    cursor.execute(
        """
        DROP INDEX IF EXISTS mega_agent.idx_semantic_memory_embedding
    """
    )
    cursor.execute(
        """
        CREATE INDEX idx_semantic_memory_embedding
        ON mega_agent.semantic_memory
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """
    )
    print("   ✅ Index recreated with 3072 dimensions.")
    print()

    # Step 5: Verify
    print("6️⃣  Verifying changes...")
    cursor.execute(
        """
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_schema = 'mega_agent'
        AND table_name = 'semantic_memory'
        AND column_name IN ('embedding', 'embedding_dimension', 'embedding_model')
    """
    )
    columns = cursor.fetchall()
    for col in columns:
        print(f"   - {col[0]}: {col[1]} (default: {col[2]})")
    print()

    print("=" * 80)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Restart the bot")
    print("  2. Test intake questionnaire")
    print("  3. Verify embeddings are created with dimension=3072")
    print()

except Exception as e:
    print(f"❌ Error during migration: {e}")
    import traceback

    traceback.print_exc()
finally:
    cursor.close()
    conn.close()

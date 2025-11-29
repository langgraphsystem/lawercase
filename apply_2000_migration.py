"""
Apply migration: 2000 dimensions + HNSW index.
"""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("SUPABASE_DB_URL or DATABASE_URL environment variable is required")

print("=" * 80)
print("MIGRATION: 2000 Dimensions + HNSW Index")
print("=" * 80)
print()

conn = psycopg2.connect(DB_URL)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

try:
    print("1. Dropping old embedding column...")
    cursor.execute("ALTER TABLE mega_agent.semantic_memory DROP COLUMN IF EXISTS embedding CASCADE")
    print("   ✅ Dropped")

    print("2. Creating new column (2000 dimensions)...")
    cursor.execute("ALTER TABLE mega_agent.semantic_memory ADD COLUMN embedding vector(2000)")
    print("   ✅ Created")

    print("3. Updating defaults...")
    cursor.execute(
        "ALTER TABLE mega_agent.semantic_memory ALTER COLUMN embedding_dimension SET DEFAULT 2000"
    )
    cursor.execute(
        "ALTER TABLE mega_agent.semantic_memory ALTER COLUMN embedding_model SET DEFAULT 'text-embedding-3-large'"
    )
    print("   ✅ Defaults updated")

    print("4. Creating HNSW index...")
    cursor.execute(
        """
        CREATE INDEX idx_semantic_memory_embedding_hnsw
        ON mega_agent.semantic_memory
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """
    )
    print("   ✅ HNSW index created")
    print()

    # Verification
    print("=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    cursor.execute(
        """
        SELECT column_name, column_default
        FROM information_schema.columns
        WHERE table_schema = 'mega_agent'
        AND table_name = 'semantic_memory'
        AND column_name IN ('embedding_dimension', 'embedding_model')
    """
    )
    cols = cursor.fetchall()
    print("Defaults:")
    for col in cols:
        print(f"   - {col[0]}: {col[1]}")
    print()

    cursor.execute(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'mega_agent'
        AND tablename = 'semantic_memory'
        AND indexdef ILIKE '%hnsw%'
    """
    )
    indexes = cursor.fetchall()
    print("HNSW indexes:")
    for idx in indexes:
        print(f"   ✅ {idx[0]}")
    print()

    print("=" * 80)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 80)
    print()
    print("📊 Configuration:")
    print("   - Dimension: 2000 (max for pgvector HNSW)")
    print("   - Index: HNSW (fast similarity search)")
    print("   - Model: text-embedding-3-large with dimensions=2000")
    print()
    print("🎯 Next steps:")
    print("   1. Restart bot to use new configuration")
    print("   2. Test intake questionnaire")
    print("   3. Verify embeddings are 2000-dimensional")
    print()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    cursor.close()
    conn.close()

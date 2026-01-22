"""
Apply migration: 3072 dimensions + HNSW indexes.
"""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("SUPABASE_DB_URL or DATABASE_URL environment variable is required")

print("=" * 80)
print("MIGRATION: 3072 Dimensions + HNSW Indexes")
print("=" * 80)
print()

conn = psycopg2.connect(DB_URL)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

try:
    print("📋 PRE-MIGRATION STATUS")
    print("-" * 80)

    # Check current semantic_memory records
    cursor.execute("SELECT COUNT(*) FROM mega_agent.semantic_memory WHERE embedding IS NOT NULL")
    sem_count = cursor.fetchone()[0]
    print(f"semantic_memory records: {sem_count}")

    # Check rfe_knowledge records
    cursor.execute("SELECT COUNT(*) FROM mega_agent.rfe_knowledge WHERE embedding IS NOT NULL")
    rfe_count = cursor.fetchone()[0]
    print(f"rfe_knowledge records: {rfe_count}")
    print()

    # =========================================================================
    # PART 1: Update semantic_memory
    # =========================================================================
    print("🔧 PART 1: Updating semantic_memory")
    print("-" * 80)

    print("1. Dropping old embedding column...")
    cursor.execute("ALTER TABLE mega_agent.semantic_memory DROP COLUMN IF EXISTS embedding CASCADE")
    print("   ✅ Dropped")

    print("2. Creating new column (3072 dimensions)...")
    cursor.execute("ALTER TABLE mega_agent.semantic_memory ADD COLUMN embedding vector(3072)")
    print("   ✅ Created")

    print("3. Updating defaults...")
    cursor.execute(
        "ALTER TABLE mega_agent.semantic_memory ALTER COLUMN embedding_dimension SET DEFAULT 3072"
    )
    cursor.execute(
        "ALTER TABLE mega_agent.semantic_memory ALTER COLUMN embedding_model SET DEFAULT 'text-embedding-3-large'"
    )
    print("   ✅ Defaults updated")

    print("4. Creating HNSW index for semantic_memory...")
    cursor.execute("""
        CREATE INDEX idx_semantic_memory_embedding_hnsw
        ON mega_agent.semantic_memory
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    print("   ✅ HNSW index created")
    print()

    # =========================================================================
    # PART 2: Create HNSW index for rfe_knowledge
    # =========================================================================
    print("🚀 PART 2: Creating HNSW index for rfe_knowledge")
    print("-" * 80)
    print(f"Building index for {rfe_count} records...")
    print("(This may take 30-60 seconds)")

    import time

    start = time.time()

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_rfe_knowledge_embedding_hnsw
        ON mega_agent.rfe_knowledge
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    elapsed = time.time() - start
    print(f"   ✅ HNSW index created in {elapsed:.1f} seconds")
    print()

    # =========================================================================
    # VERIFICATION
    # =========================================================================
    print("✅ VERIFICATION")
    print("-" * 80)

    # Check columns
    cursor.execute("""
        SELECT column_name, column_default
        FROM information_schema.columns
        WHERE table_schema = 'mega_agent'
        AND table_name = 'semantic_memory'
        AND column_name IN ('embedding_dimension', 'embedding_model')
    """)
    cols = cursor.fetchall()
    print("semantic_memory defaults:")
    for col in cols:
        print(f"   - {col[0]}: {col[1]}")
    print()

    # Check indexes
    cursor.execute("""
        SELECT tablename, indexname
        FROM pg_indexes
        WHERE schemaname = 'mega_agent'
        AND tablename IN ('semantic_memory', 'rfe_knowledge')
        AND indexdef ILIKE '%hnsw%'
        ORDER BY tablename
    """)
    indexes = cursor.fetchall()
    print("HNSW indexes:")
    for idx in indexes:
        print(f"   ✅ {idx[0]}.{idx[1]}")
    print()

    print("=" * 80)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 80)
    print()
    print("📊 SUMMARY:")
    print("   - semantic_memory: 3072 dimensions + HNSW index")
    print(f"   - rfe_knowledge: HNSW index ({rfe_count} records)")
    print()
    print("🎯 NEXT STEPS:")
    print("   1. Code changes already made (config.py, models.py, supabase_embedder.py)")
    print("   2. Continue with startup health check, logging, error handling")
    print("   3. Commit and push to Railway")
    print("   4. Test intake questionnaire")
    print()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    cursor.close()
    conn.close()

"""
Check vector index type used in rfe_knowledge table.
"""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("SUPABASE_DB_URL or DATABASE_URL environment variable is required")

print("=" * 80)
print("CHECKING RFE_KNOWLEDGE VECTOR INDEX")
print("=" * 80)
print()

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

try:
    # 1. Check all indexes on rfe_knowledge
    print("1️⃣  All indexes on mega_agent.rfe_knowledge...")
    cursor.execute(
        """
        SELECT
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'mega_agent'
        AND tablename = 'rfe_knowledge'
        ORDER BY indexname
    """
    )
    indexes = cursor.fetchall()

    if indexes:
        print(f"   Found {len(indexes)} index(es):")
        for idx in indexes:
            print(f"\n   📊 Index: {idx['indexname']}")
            print(f"   Definition: {idx['indexdef']}")

            # Detect index type
            indexdef = idx["indexdef"].lower()
            if "ivfflat" in indexdef:
                print("   Type: ✅ IVFFlat (max 2000 dimensions)")
            elif "hnsw" in indexdef:
                print("   Type: ✅ HNSW (supports >2000 dimensions)")
            elif "vector" in indexdef:
                print("   Type: ⚠️  Vector index (type unclear)")
            else:
                print("   Type: Regular index (not vector)")
    else:
        print("   ❌ No indexes found!")
    print()

    # 2. Check pgvector extension version
    print("2️⃣  Checking pgvector extension version...")
    cursor.execute(
        """
        SELECT
            extname,
            extversion
        FROM pg_extension
        WHERE extname = 'vector'
    """
    )
    ext = cursor.fetchone()

    if ext:
        version = ext["extversion"]
        print(f"   pgvector version: {version}")

        # Version compatibility
        major_minor = version.split(".")[:2]
        ver_num = float(".".join(major_minor))

        if ver_num >= 0.5:
            print(f"   ✅ Version {version} supports HNSW index (3072 dimensions OK)")
        elif ver_num >= 0.4:
            print(f"   ⚠️  Version {version} supports only IVFFlat (max 2000 dimensions)")
        else:
            print(f"   ⚠️  Version {version} - old version")
    else:
        print("   ❌ pgvector extension not found!")
    print()

    # 3. Check table structure
    print("3️⃣  Checking rfe_knowledge table structure...")
    cursor.execute(
        """
        SELECT
            column_name,
            data_type,
            udt_name
        FROM information_schema.columns
        WHERE table_schema = 'mega_agent'
        AND table_name = 'rfe_knowledge'
        ORDER BY ordinal_position
    """
    )
    columns = cursor.fetchall()

    print("   Columns:")
    for col in columns:
        if col["udt_name"] == "vector":
            print(f"   - {col['column_name']}: {col['udt_name']} ✅ (vector column)")
        else:
            print(f"   - {col['column_name']}: {col['data_type']}")
    print()

    # 4. Summary
    print("=" * 80)
    print("SUMMARY & RECOMMENDATION")
    print("=" * 80)
    print()

    print("📋 RFE Knowledge Base:")
    print("   - Embeddings: 5626 records")
    print("   - Dimension: 3072 (text-embedding-3-large full)")
    print()

    if indexes:
        has_ivfflat = any("ivfflat" in idx["indexdef"].lower() for idx in indexes)
        has_hnsw = any("hnsw" in idx["indexdef"].lower() for idx in indexes)

        if has_hnsw:
            print("✅ RFE uses HNSW index → supports 3072 dimensions")
            print()
            print("🎯 RECOMMENDATION for semantic_memory:")
            print("   1. Use 3072 dimensions (same as RFE)")
            print("   2. Use HNSW index (not IVFFlat)")
            print("   3. Maintain consistency across all tables")
        elif has_ivfflat:
            print("⚠️  RFE uses IVFFlat index BUT has 3072 dimensions!")
            print("   This is a problem - IVFFlat max is 2000!")
            print()
            print("🎯 RECOMMENDATION for semantic_memory:")
            print("   Option A: Use HNSW index + 3072 dimensions (match RFE)")
            print("   Option B: Migrate RFE to HNSW as well")
        else:
            print("⚠️  RFE has NO vector index!")
            print("   Vector search will be slow without index")
            print()
            print("🎯 RECOMMENDATION for semantic_memory:")
            print("   1. Use 3072 dimensions (same as RFE)")
            print("   2. Create HNSW index for both tables")
    else:
        print("⚠️  No indexes on rfe_knowledge!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    cursor.close()
    conn.close()

"""
Check RFE embeddings dimensions using pgvector functions.
"""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("SUPABASE_DB_URL or DATABASE_URL environment variable is required")

print("=" * 80)
print("CHECKING RFE EMBEDDINGS DIMENSIONS")
print("=" * 80)
print()

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

try:
    # 1. Check rfe_knowledge table
    print("1️⃣  Checking mega_agent.rfe_knowledge table...")
    cursor.execute(
        """
        SELECT COUNT(*) as total
        FROM mega_agent.rfe_knowledge
        WHERE embedding IS NOT NULL
    """
    )
    total = cursor.fetchone()["total"]
    print(f"   Total records with embeddings: {total}")
    print()

    if total > 0:
        # 2. Get embedding dimension using vector_dims()
        print("2️⃣  Getting embedding dimensions...")
        cursor.execute(
            """
            SELECT
                vector_dims(embedding) as dimension,
                COUNT(*) as count
            FROM mega_agent.rfe_knowledge
            WHERE embedding IS NOT NULL
            GROUP BY vector_dims(embedding)
            ORDER BY count DESC
        """
        )
        dimensions = cursor.fetchall()

        print("   Dimensions found:")
        for dim in dimensions:
            percentage = (dim["count"] / total) * 100
            print(f"   - {dim['dimension']} dimensions: {dim['count']} records ({percentage:.1f}%)")
        print()

        # 3. Check embedding_model if exists
        print("3️⃣  Checking embedding model info...")
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'mega_agent'
            AND table_name = 'rfe_knowledge'
            AND column_name IN ('embedding_model', 'model', 'embedding_dimension')
        """
        )
        model_columns = cursor.fetchall()

        if model_columns:
            for col in model_columns:
                col_name = col["column_name"]
                cursor.execute(
                    f"""
                    SELECT {col_name}, COUNT(*) as count
                    FROM mega_agent.rfe_knowledge
                    GROUP BY {col_name}
                    ORDER BY count DESC
                    LIMIT 5
                """
                )
                values = cursor.fetchall()
                print(f"   Column '{col_name}':")
                for v in values:
                    print(f"   - {v[col_name]}: {v['count']} records")
        else:
            print("   ⚠️  No model info columns found")
        print()

        # 4. Sample first record
        print("4️⃣  Sample record (first)...")
        cursor.execute(
            """
            SELECT
                id,
                vector_dims(embedding) as dimension,
                chunk_text,
                metadata
            FROM mega_agent.rfe_knowledge
            WHERE embedding IS NOT NULL
            LIMIT 1
        """
        )
        sample = cursor.fetchone()
        if sample:
            print(f"   ID: {sample['id']}")
            print(f"   Dimension: {sample['dimension']}")
            print(f"   Chunk preview: {sample['chunk_text'][:100]}...")
            print(f"   Metadata: {sample['metadata']}")
        print()

        # 5. Check index on embeddings
        print("5️⃣  Checking vector indexes...")
        cursor.execute(
            """
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'mega_agent'
            AND tablename = 'rfe_knowledge'
            AND indexdef ILIKE '%vector%'
        """
        )
        indexes = cursor.fetchall()
        if indexes:
            print(f"   Found {len(indexes)} vector index(es):")
            for idx in indexes:
                print(f"   - {idx['indexname']}")
                # Extract index type (ivfflat or hnsw)
                if "ivfflat" in idx["indexdef"].lower():
                    print("     Type: IVFFlat (max 2000 dimensions)")
                elif "hnsw" in idx["indexdef"].lower():
                    print("     Type: HNSW (supports >2000 dimensions)")
                else:
                    print("     Type: Unknown")
        else:
            print("   ⚠️  No vector indexes found")
        print()

    # 6. Summary
    print("=" * 80)
    print("SUMMARY & RECOMMENDATION")
    print("=" * 80)
    print()

    if total > 0 and dimensions:
        primary_dim = dimensions[0]["dimension"]
        print(f"✅ RFE Knowledge Base uses: {primary_dim} dimensions")
        print(f"   ({dimensions[0]['count']} records out of {total} total)")
        print()

        print("🎯 RECOMMENDATION FOR semantic_memory:")
        print(f"   Use the SAME dimension: {primary_dim}")
        print()
        print("   Reasons:")
        print("   1. Consistency with existing RFE embeddings")
        print("   2. Same model/infrastructure")
        print("   3. Unified vector search across all tables")
        print()

        if primary_dim <= 2000:
            print(f"   ✅ {primary_dim} dimensions: Compatible with IVFFlat index")
        else:
            print(f"   ⚠️  {primary_dim} dimensions: Requires HNSW index (IVFFlat max is 2000)")

    else:
        print("❌ No RFE embeddings found!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    cursor.close()
    conn.close()

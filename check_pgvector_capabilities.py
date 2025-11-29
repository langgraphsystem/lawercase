"""
Check pgvector version and dimension limits.
"""

from __future__ import annotations

import os

import psycopg2

DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("SUPABASE_DB_URL or DATABASE_URL environment variable is required")

print("=" * 80)
print("PGVECTOR CAPABILITIES CHECK")
print("=" * 80)
print()

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

try:
    # Check pgvector version
    cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    version = cursor.fetchone()[0]
    print(f"pgvector version: {version}")
    print()

    # Check documentation/limits
    print("KNOWN LIMITS:")
    print("  - IVFFlat: max 2000 dimensions")
    print("  - HNSW: max 2000 dimensions (as of pgvector 0.8.0)")
    print()

    # Check RFE status
    print("RFE KNOWLEDGE STATUS:")
    cursor.execute(
        """
        SELECT
            COUNT(*) as count,
            vector_dims(embedding) as dimension
        FROM mega_agent.rfe_knowledge
        WHERE embedding IS NOT NULL
        GROUP BY vector_dims(embedding)
    """
    )
    rfe = cursor.fetchone()
    print(f"  - Records: {rfe[0]}")
    print(f"  - Dimension: {rfe[1]}")
    print()

    # Check if RFE has indexes
    cursor.execute(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'mega_agent'
        AND tablename = 'rfe_knowledge'
        AND (indexdef ILIKE '%ivfflat%' OR indexdef ILIKE '%hnsw%')
    """
    )
    rfe_indexes = cursor.fetchall()

    if rfe_indexes:
        print("RFE VECTOR INDEXES:")
        for idx in rfe_indexes:
            print(f"  - {idx[0]}: {idx[1]}")
    else:
        print("RFE VECTOR INDEXES: ❌ NONE (uses sequential scan!)")
    print()

    # Test vector search performance without index
    import time

    print("TESTING VECTOR SEARCH PERFORMANCE:")
    print("  (Random query on rfe_knowledge without index)")

    # Get a sample embedding
    cursor.execute(
        """
        SELECT embedding
        FROM mega_agent.rfe_knowledge
        LIMIT 1
    """
    )
    sample_emb = cursor.fetchone()[0]

    # Measure search time
    start = time.time()
    cursor.execute(
        """
        SELECT criterion, issue_type, 1 - (embedding <=> %s::vector) as similarity
        FROM mega_agent.rfe_knowledge
        ORDER BY embedding <=> %s::vector
        LIMIT 5
    """,
        (sample_emb, sample_emb),
    )
    results = cursor.fetchall()
    elapsed = (time.time() - start) * 1000  # ms

    print(f"  - Search time: {elapsed:.1f}ms (5626 records, no index)")
    print(f"  - Top result similarity: {results[0][2]:.4f}")
    print()

    print("=" * 80)
    print("AVAILABLE OPTIONS")
    print("=" * 80)
    print()

    print("Option 1: Use 1536 dimensions (with index)")
    print("  ✅ Pros: IVFFlat/HNSW index support, fast search")
    print("  ❌ Cons: Lower quality embeddings than 3072")
    print("  📝 OpenAI API parameter: dimensions=1536")
    print()

    print("Option 2: Use 2000 dimensions (with index)")
    print("  ✅ Pros: Max for IVFFlat/HNSW, better than 1536")
    print("  ❌ Cons: Still lower quality than 3072")
    print("  📝 OpenAI API parameter: dimensions=2000")
    print()

    print("Option 3: Keep 3072 dimensions (NO index)")
    print("  ✅ Pros: Best quality embeddings")
    print("  ❌ Cons: Sequential scan, slower search")
    print(f"  📊 Current performance: ~{elapsed:.0f}ms for 5626 records")
    print("  📈 Scalability: Linear O(n) - slow for 100k+ records")
    print()

    print("Option 4: Hybrid approach")
    print("  ✅ Store 3072 dimensions, create 2000-dim projection for search")
    print("  ✅ Best of both worlds: quality + speed")
    print("  ❌ More complex implementation")
    print()

    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print()

    if elapsed < 100:
        print(f"✅ Current search is FAST ({elapsed:.0f}ms) even without index!")
        print()
        print("🎯 Recommended: Option 3 (Keep 3072, no index)")
        print()
        print("Reasoning:")
        print(f"  - {rfe[0]} records search in {elapsed:.0f}ms is acceptable")
        print("  - Best embedding quality for RAG")
        print("  - Consistent with existing RFE knowledge")
        print("  - Can add projection later if needed")
    else:
        print(f"⚠️  Current search is SLOW ({elapsed:.0f}ms) without index")
        print()
        print("🎯 Recommended: Option 2 (Use 2000 dimensions)")
        print()
        print("Reasoning:")
        print("  - Need index for acceptable performance")
        print("  - 2000 dimensions is max for HNSW")
        print("  - Better than 1536, good enough for most use cases")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    cursor.close()
    conn.close()

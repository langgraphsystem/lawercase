"""
Check existing embeddings dimensions in Supabase database.
"""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("SUPABASE_DB_URL or DATABASE_URL environment variable is required")

print("=" * 80)
print("CHECKING EXISTING EMBEDDINGS IN SUPABASE")
print("=" * 80)
print()

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

try:
    # 1. Check all tables with vector columns
    print("1️⃣  Finding all tables with vector embeddings...")
    cursor.execute(
        """
        SELECT
            table_schema,
            table_name,
            column_name,
            udt_name,
            character_maximum_length
        FROM information_schema.columns
        WHERE udt_name = 'vector'
        ORDER BY table_schema, table_name
    """
    )

    vector_tables = cursor.fetchall()

    if vector_tables:
        print(f"   Found {len(vector_tables)} table(s) with vector columns:")
        for tbl in vector_tables:
            print(f"   - {tbl['table_schema']}.{tbl['table_name']}.{tbl['column_name']}")
    else:
        print("   ❌ No tables with vector columns found!")
        exit(0)
    print()

    # 2. For each table, check actual embedding dimensions
    print("2️⃣  Checking actual embedding dimensions in data...")
    print()

    for tbl in vector_tables:
        schema = tbl["table_schema"]
        table = tbl["table_name"]
        column = tbl["column_name"]

        print(f"   📊 Table: {schema}.{table}")
        print(f"   ├─ Column: {column}")

        # Count records
        cursor.execute(
            f"""
            SELECT COUNT(*) as count
            FROM {schema}.{table}
            WHERE {column} IS NOT NULL
        """
        )
        count = cursor.fetchone()["count"]
        print(f"   ├─ Records with embeddings: {count}")

        if count > 0:
            # Get sample embedding dimension
            cursor.execute(
                f"""
                SELECT
                    array_length({column}, 1) as dimension,
                    COUNT(*) as count
                FROM {schema}.{table}
                WHERE {column} IS NOT NULL
                GROUP BY array_length({column}, 1)
                ORDER BY count DESC
            """
            )
            dimensions = cursor.fetchall()

            print("   ├─ Dimensions found:")
            for dim in dimensions:
                print(f"   │  ├─ {dim['dimension']} dimensions: {dim['count']} records")

            # Check if there's an embedding_model column
            cursor.execute(
                f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = '{schema}'
                AND table_name = '{table}'
                AND column_name IN ('embedding_model', 'model', 'embedding_dimension')
            """
            )
            model_columns = cursor.fetchall()

            if model_columns:
                print(f"   ├─ Model info columns: {[c['column_name'] for c in model_columns]}")

                # Get model info
                model_col = model_columns[0]["column_name"]
                cursor.execute(
                    f"""
                    SELECT {model_col}, COUNT(*) as count
                    FROM {schema}.{table}
                    GROUP BY {model_col}
                    ORDER BY count DESC
                    LIMIT 5
                """
                )
                models = cursor.fetchall()
                print("   └─ Models used:")
                for m in models:
                    print(f"      └─ {m[model_col]}: {m['count']} records")
            else:
                print("   └─ No model info columns found")
        else:
            print("   └─ ⚠️  No records with embeddings")

        print()

    # 3. Check RFE-specific tables
    print("3️⃣  Checking RFE (Reference Feature Extraction) tables...")
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND (
            table_name ILIKE '%rfe%'
            OR table_name ILIKE '%reference%'
            OR table_name ILIKE '%chunk%'
            OR table_name ILIKE '%document%'
        )
        ORDER BY table_name
    """
    )

    rfe_tables = cursor.fetchall()
    if rfe_tables:
        print(f"   Found {len(rfe_tables)} potential RFE table(s):")
        for t in rfe_tables:
            print(f"   - {t['table_name']}")

            # Check if it has embeddings
            cursor.execute(
                f"""
                SELECT column_name, udt_name
                FROM information_schema.columns
                WHERE table_name = '{t['table_name']}'
                AND udt_name = 'vector'
            """
            )
            vec_cols = cursor.fetchall()
            if vec_cols:
                print(f"     ✅ Has vector column: {vec_cols[0]['column_name']}")
            else:
                print("     ❌ No vector columns")
    else:
        print("   No RFE-related tables found")
    print()

    # 4. Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    if vector_tables:
        print("📋 Vector tables found:")
        for tbl in vector_tables:
            print(f"   - {tbl['table_schema']}.{tbl['table_name']}.{tbl['column_name']}")
        print()

        print("🎯 RECOMMENDATION:")
        print("   Based on existing embeddings, you should use the SAME dimension")
        print("   to ensure compatibility with existing vector search infrastructure.")
    else:
        print("❌ No existing vector embeddings found in database!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
finally:
    cursor.close()
    conn.close()

from __future__ import annotations

import asyncio
import json

import asyncpg


async def check():
    dsn = "postgresql://postgres.whcapsehbgreeumpfnil:Magdi2085!@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
    user_id = "7314014306"

    conn = await asyncpg.connect(dsn, statement_cache_size=0)

    rows = await conn.fetch(
        """
        SELECT
            metadata_json->>'document_type_name' as doc_type,
            metadata_json->>'extracted_fields' as extracted,
            metadata_json,
            created_at
        FROM mega_agent.semantic_memory
        WHERE user_id = $1
        AND metadata_json->>'source' = 'smart_document_upload'
        ORDER BY created_at DESC
        LIMIT 3
    """,
        user_id,
    )

    print("Documents:")
    for row in rows:
        print(f"\nType: {row['doc_type']}")
        print(f"Created: {row['created_at']}")

        extracted = row["extracted"]
        if extracted:
            print(f"Extracted fields: {extracted[:200]}...")
        else:
            print("Extracted fields: None")

        # Check full metadata for clues
        meta = row["metadata_json"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        print(f"Has extracted_fields key: {'extracted_fields' in meta}")

    await conn.close()


asyncio.run(check())

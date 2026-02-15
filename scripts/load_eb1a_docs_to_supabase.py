#!/usr/bin/env python3
"""
Load EB-1A USCIS documents to Supabase knowledge base.
Exports to JSON and imports to Supabase.
"""

from __future__ import annotations

from datetime import datetime
import gc
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

# Configuration
EB1A_DOCS_PATH = Path(__file__).parent.parent / "knowledge_base" / "legal" / "uscis_eb1a"
INDEX_FILE = EB1A_DOCS_PATH / "index.json"
OUTPUT_FILE = EB1A_DOCS_PATH / "knowledge_base_export.json"

# Supabase config
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")


def get_supabase_client():
    """Get Supabase client."""
    from supabase import create_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def load_index() -> dict:
    """Load the index.json file."""
    with open(INDEX_FILE, encoding="utf-8") as f:
        return json.load(f)


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 50) -> str:
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        text_parts = []

        for page_idx, page in enumerate(doc):
            if page_idx >= max_pages:
                break
            page_text = page.get_text()
            if page_text:
                text_parts.append(page_text)

        doc.close()
        del doc
        gc.collect()

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"    - PDF error: {e}")
        return ""


def split_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    """Split text into smaller chunks."""
    if not text or len(text) < 100:
        return []

    if len(text) > 100000:
        text = text[:100000]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        if end < text_len:
            for sep in ["\n\n", ". ", "\n", " "]:
                break_point = text.rfind(sep, start + chunk_size // 2, end)
                if break_point > start:
                    end = break_point + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk and len(chunk) > 50:
            chunks.append(chunk)

        start = end - overlap if end < text_len else text_len

        if len(chunks) > 100:
            break

    return chunks


def generate_chunk_id(content: str, doc_id: str, chunk_idx: int) -> str:
    unique_str = f"{doc_id}-{chunk_idx}-{content[:50]}"
    return hashlib.md5(unique_str.encode(), usedforsecurity=False).hexdigest()


def process_document(doc_path: Path, metadata_base: dict) -> list[dict]:
    """Process a single document and return chunks."""
    records = []

    if doc_path.suffix == ".pdf":
        text = extract_text_from_pdf(doc_path)
    elif doc_path.suffix == ".md":
        with open(doc_path, encoding="utf-8") as f:
            text = f.read()
    else:
        return records

    if not text:
        return records

    chunks = split_text(text)

    if not chunks:
        return records

    print(f"    - {len(chunks)} chunks")

    for chunk_idx, chunk in enumerate(chunks):
        metadata = {
            **metadata_base,
            "chunk_index": chunk_idx,
            "total_chunks": len(chunks),
            "imported_at": datetime.now().isoformat(),
        }

        chunk_id = generate_chunk_id(chunk, metadata_base["document_id"], chunk_idx)

        records.append(
            {
                "id": chunk_id,
                "content": chunk,
                "metadata": metadata,
                "namespace": "eb1a",
                "created_at": datetime.now().isoformat(),
            }
        )

    del chunks
    del text
    gc.collect()

    return records


def export_documents():
    """Export all EB-1A documents to JSON."""

    print("=" * 60)
    print("EB-1A Documents Export")
    print("=" * 60)

    index = load_index()
    print(f"\nCollection: {index['collection']}")

    all_records = []

    # Process markdown guide first
    guide_path = EB1A_DOCS_PATH / "EB1A_COMPLETE_GUIDE.md"
    if guide_path.exists():
        print("\n[PROCESS] EB1A_COMPLETE_GUIDE.md...")
        metadata = {
            "source": "uscis",
            "document_type": "guide",
            "document_id": "eb1a-complete-guide",
            "document_name": "EB-1A Complete Guide",
            "description": "Comprehensive EB-1A guide",
            "collection": "eb1a_knowledge_base",
        }
        records = process_document(guide_path, metadata)
        all_records.extend(records)
        gc.collect()

    # Process documents from each category
    for category_name, category_data in index["categories"].items():
        print(f"\n--- {category_name.upper()} ---")

        for doc in category_data["documents"]:
            doc_path = EB1A_DOCS_PATH / doc["file"]

            if not doc_path.exists():
                print(f"  [SKIP] {doc['name']}")
                continue

            print(f"  [PROCESS] {doc['name']}...")

            metadata = {
                "source": "uscis",
                "document_type": category_name,
                "document_id": doc["id"],
                "document_name": doc["name"],
                "description": doc["description"],
                "url": doc.get("url", ""),
                "file_path": str(doc["file"]),
                "collection": "eb1a_knowledge_base",
            }

            try:
                records = process_document(doc_path, metadata)
                all_records.extend(records)
            except Exception as e:
                print(f"    - Error: {e}")

            gc.collect()

    # Save to JSON
    print(f"\n--- Saving to {OUTPUT_FILE} ---")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("COMPLETE!")
    print(f"  Total records: {len(all_records)}")
    print(f"  Output file: {OUTPUT_FILE}")
    print("=" * 60)

    return all_records


def import_to_supabase(batch_size: int = 50):
    """Import JSON data to Supabase."""

    print("=" * 60)
    print("Import to Supabase")
    print("=" * 60)

    # Load JSON data
    if not OUTPUT_FILE.exists():
        print(f"[ERROR] Export file not found: {OUTPUT_FILE}")
        print("Run without --import first to export documents")
        return

    print(f"\nLoading {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        records = json.load(f)

    print(f"Loaded {len(records)} records")

    # Connect to Supabase
    try:
        supabase = get_supabase_client()
        print("Connected to Supabase")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return

    # Check if table exists by trying a simple query
    try:
        result = supabase.table("knowledge_base").select("id").limit(1).execute()
        print("Table 'knowledge_base' exists")
    except Exception as e:
        print("\n[ERROR] Table 'knowledge_base' does not exist!")
        print("\nPlease create the table first by running this SQL in Supabase:")
        print("-" * 50)
        print(
            """
CREATE TABLE IF NOT EXISTS knowledge_base (
    id VARCHAR(255) PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    namespace VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kb_namespace ON knowledge_base(namespace);
CREATE INDEX IF NOT EXISTS idx_kb_metadata ON knowledge_base USING GIN(metadata);
"""
        )
        print("-" * 50)
        return

    # Import in batches
    total = len(records)
    imported = 0
    errors = 0

    print(f"\nImporting {total} records in batches of {batch_size}...")

    for batch_start in range(0, total, batch_size):
        batch = records[batch_start : batch_start + batch_size]

        try:
            supabase.table("knowledge_base").upsert(batch).execute()
            imported += len(batch)
            print(f"  [{imported}/{total}] Imported batch {batch_start // batch_size + 1}")
        except Exception as e:
            errors += len(batch)
            print(f"  [ERROR] Batch {batch_start // batch_size + 1}: {e}")

        time.sleep(0.1)

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE!")
    print(f"  Imported: {imported}")
    print(f"  Errors: {errors}")
    print("=" * 60)


def verify_import():
    """Verify documents in Supabase."""
    print("\n--- Verification ---")

    try:
        supabase = get_supabase_client()

        # Count total
        result = (
            supabase.table("knowledge_base")
            .select("id", count="exact")
            .eq("namespace", "eb1a")
            .execute()
        )
        count = result.count if hasattr(result, "count") else len(result.data)
        print(f"Total EB-1A chunks in Supabase: {count}")

        # Get unique documents
        result = (
            supabase.table("knowledge_base")
            .select("metadata")
            .eq("namespace", "eb1a")
            .limit(100)
            .execute()
        )
        if result.data:
            docs = set()
            for row in result.data:
                doc_name = row.get("metadata", {}).get("document_name")
                if doc_name:
                    docs.add(doc_name)
            print(f"Unique documents: {len(docs)}")
            for doc in sorted(docs)[:10]:
                print(f"  - {doc}")

        # Test search
        print("\n--- Test Search ---")
        result = (
            supabase.table("knowledge_base")
            .select("content", "metadata")
            .eq("namespace", "eb1a")
            .ilike("content", "%extraordinary ability%")
            .limit(3)
            .execute()
        )
        if result.data:
            print(f"Found {len(result.data)} results for 'extraordinary ability'")
            for row in result.data[:2]:
                doc = row.get("metadata", {}).get("document_name", "Unknown")
                content = row.get("content", "")[:100]
                print(f"  - {doc}: {content}...")
        else:
            print("No results found")

    except Exception as e:
        print(f"Verification error: {e}")


def create_sql_file():
    """Create SQL file for table creation."""
    sql_file = EB1A_DOCS_PATH / "create_knowledge_base_table.sql"
    sql_content = """-- Create knowledge_base table for RAG/vector search
-- Run this in Supabase SQL Editor BEFORE importing data

-- Enable pgvector extension (if not already enabled)
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_base (
    id VARCHAR(255) PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    namespace VARCHAR(100) DEFAULT 'default',
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_kb_namespace ON knowledge_base(namespace);
CREATE INDEX IF NOT EXISTS idx_kb_metadata ON knowledge_base USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_kb_created_at ON knowledge_base(created_at DESC);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_kb_content_fts ON knowledge_base
USING GIN(to_tsvector('english', content));

-- Add comment
COMMENT ON TABLE knowledge_base IS 'RAG knowledge base for document chunks and embeddings';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_base TO authenticated;
-- GRANT SELECT ON knowledge_base TO anon;
"""
    with open(sql_file, "w", encoding="utf-8") as f:
        f.write(sql_content)
    print(f"SQL file created: {sql_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EB-1A Documents to Supabase")
    parser.add_argument("--export", action="store_true", help="Export documents to JSON")
    parser.add_argument(
        "--import", dest="do_import", action="store_true", help="Import JSON to Supabase"
    )
    parser.add_argument("--verify", action="store_true", help="Verify import in Supabase")
    parser.add_argument("--sql", action="store_true", help="Create SQL file for table")
    parser.add_argument("--all", action="store_true", help="Export and import all")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for import")

    args = parser.parse_args()

    # Default to export if no args
    if not any([args.export, args.do_import, args.verify, args.sql, args.all]):
        args.export = True

    if args.sql or args.all:
        create_sql_file()

    if args.export or args.all:
        export_documents()

    if args.do_import or args.all:
        import_to_supabase(batch_size=args.batch_size)

    if args.verify or args.all or args.do_import:
        verify_import()

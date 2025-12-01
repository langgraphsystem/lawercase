"""Migration: Create mega_agent schema and all required tables.

This script creates the mega_agent schema and all tables required by the application.
Run this on production Supabase before deploying.

Usage:
    railway run python migrations/create_mega_agent_schema.py
"""

import os

import psycopg2  # type: ignore[import-untyped]
from psycopg2 import sql

# Get database URL from environment
DB_URL = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")


def create_schema_and_tables():
    """Create mega_agent schema and all tables using psycopg2 (sync)."""
    if not DB_URL:
        print("❌ No database URL found. Set POSTGRES_DSN or DATABASE_URL environment variable.")
        return False

    # Convert asyncpg URL to psycopg2 format
    db_url = DB_URL
    if "+asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    print("🔗 Connecting to database...")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True  # Required for CREATE SCHEMA
        cur = conn.cursor()

        # 1. Create mega_agent schema
        print("\n📦 Creating mega_agent schema...")
        cur.execute("CREATE SCHEMA IF NOT EXISTS mega_agent")
        print("✅ Schema mega_agent created")

        # 2. Enable pgvector extension
        print("\n📦 Enabling pgvector extension...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("✅ pgvector extension enabled")

        # 3. Create cases table
        print("\n📦 Creating cases table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mega_agent.cases (
                case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(255) NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'draft',
                case_type VARCHAR(100),
                data JSONB DEFAULT '{}',
                version INTEGER DEFAULT 1,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                deleted_at TIMESTAMPTZ,
                CONSTRAINT case_title_not_empty CHECK (length(title) > 0),
                CONSTRAINT case_status_valid CHECK (status IN ('draft', 'open', 'in_progress', 'closed', 'archived'))
            )
        """
        )
        print("✅ mega_agent.cases created")

        # Create indexes for cases
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_user_id ON mega_agent.cases(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON mega_agent.cases(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_created ON mega_agent.cases(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_data ON mega_agent.cases USING gin(data)")
        print("✅ Cases indexes created")

        # 4. Create semantic_memory table
        print("\n📦 Creating semantic_memory table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mega_agent.semantic_memory (
                record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                namespace VARCHAR(255) DEFAULT 'default',
                user_id VARCHAR(255) NOT NULL,
                thread_id VARCHAR(255),
                text TEXT NOT NULL,
                type VARCHAR(50) DEFAULT 'fact',
                source VARCHAR(100),
                tags TEXT[] DEFAULT ARRAY[]::TEXT[],
                metadata_json JSONB DEFAULT '{}',
                embedding vector(2000),
                embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-large',
                embedding_dimension INTEGER DEFAULT 2000,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                CONSTRAINT semantic_text_not_empty CHECK (length(text) > 0)
            )
        """
        )
        print("✅ mega_agent.semantic_memory created")

        # Create indexes for semantic_memory
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_semantic_user_id ON mega_agent.semantic_memory(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_semantic_namespace ON mega_agent.semantic_memory(namespace)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_semantic_type ON mega_agent.semantic_memory(type)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_semantic_tags ON mega_agent.semantic_memory USING gin(tags)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_semantic_created ON mega_agent.semantic_memory(created_at)"
        )
        print("✅ Semantic memory indexes created")

        # 5. Create HNSW index for vector search
        print("\n📦 Creating HNSW vector index...")
        try:
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_semantic_embedding_hnsw
                ON mega_agent.semantic_memory
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """
            )
            print("✅ HNSW vector index created")
        except Exception as e:
            print(f"⚠️ HNSW index creation skipped: {e}")

        # 6. Create episodic_memory table
        print("\n📦 Creating episodic_memory table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mega_agent.episodic_memory (
                event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(255) NOT NULL,
                thread_id VARCHAR(255),
                source VARCHAR(100) NOT NULL,
                action VARCHAR(100) NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                payload JSONB DEFAULT '{}',
                CONSTRAINT episodic_source_not_empty CHECK (length(source) > 0),
                CONSTRAINT episodic_action_not_empty CHECK (length(action) > 0)
            )
        """
        )
        print("✅ mega_agent.episodic_memory created")

        # Create indexes for episodic_memory
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_episodic_user_id ON mega_agent.episodic_memory(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_episodic_thread_id ON mega_agent.episodic_memory(thread_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_episodic_source ON mega_agent.episodic_memory(source)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_episodic_action ON mega_agent.episodic_memory(action)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON mega_agent.episodic_memory(timestamp)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_episodic_payload ON mega_agent.episodic_memory USING gin(payload)"
        )
        print("✅ Episodic memory indexes created")

        # 7. Create documents table
        print("\n📦 Creating documents table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mega_agent.documents (
                document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                case_id UUID REFERENCES mega_agent.cases(case_id) ON DELETE CASCADE,
                user_id VARCHAR(255) NOT NULL,
                filename TEXT NOT NULL,
                document_type VARCHAR(50) DEFAULT 'general',
                r2_key TEXT NOT NULL,
                r2_bucket VARCHAR(100),
                mime_type VARCHAR(100),
                file_size BIGINT,
                metadata_json JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                CONSTRAINT doc_filename_not_empty CHECK (length(filename) > 0),
                CONSTRAINT doc_r2_key_not_empty CHECK (length(r2_key) > 0)
            )
        """
        )
        print("✅ mega_agent.documents created")

        # Create indexes for documents
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_case_id ON mega_agent.documents(case_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_user_id ON mega_agent.documents(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_type ON mega_agent.documents(document_type)"
        )
        print("✅ Documents indexes created")

        # 8. Create intake_answers table
        print("\n📦 Creating intake_answers table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mega_agent.intake_answers (
                answer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                case_id UUID REFERENCES mega_agent.cases(case_id) ON DELETE CASCADE,
                user_id VARCHAR(255) NOT NULL,
                question_key VARCHAR(255) NOT NULL,
                question_text TEXT,
                answer_value TEXT,
                answer_data JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """
        )
        print("✅ mega_agent.intake_answers created")

        # Create indexes for intake_answers
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_intake_case_id ON mega_agent.intake_answers(case_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_intake_user_id ON mega_agent.intake_answers(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_intake_question_key ON mega_agent.intake_answers(question_key)"
        )
        print("✅ Intake answers indexes created")

        # Verify all tables exist
        print("\n🔍 Verifying created tables...")
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'mega_agent'
            ORDER BY table_name
        """
        )
        tables = [row[0] for row in cur.fetchall()]
        print(f"✅ Tables in mega_agent schema: {tables}")

        expected_tables = [
            "cases",
            "documents",
            "episodic_memory",
            "intake_answers",
            "semantic_memory",
        ]
        missing = set(expected_tables) - set(tables)
        if missing:
            print(f"⚠️ Missing tables: {missing}")
            return False

        cur.close()
        conn.close()

        print("\n✅ All tables created successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_schema_and_tables()
    exit(0 if success else 1)

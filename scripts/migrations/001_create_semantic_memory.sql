-- Migration: Create semantic_memory table
-- Run this in Supabase Dashboard -> SQL Editor
-- https://supabase.com/dashboard/project/whcapsehbgreeumpfnil/sql

-- 1. Enable pgvector extension (if not enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create mega_agent schema (if not exists)
CREATE SCHEMA IF NOT EXISTS mega_agent;

-- 3. Grant usage on schema to service role
GRANT USAGE ON SCHEMA mega_agent TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA mega_agent TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA mega_agent GRANT ALL ON TABLES TO service_role;

-- 4. Create semantic_memory table
CREATE TABLE IF NOT EXISTS mega_agent.semantic_memory (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Namespace / tenancy
    namespace VARCHAR(255) DEFAULT 'default',

    -- Ownership
    user_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255),
    case_id VARCHAR(255),  -- Added for intake questionnaire linking

    -- Content
    text TEXT NOT NULL CHECK (length(text) > 0),
    type VARCHAR(50) DEFAULT 'fact',
    source VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    metadata_json JSONB DEFAULT '{}',

    -- Embedding (pgvector) - 2000 dimensions for text-embedding-3-large
    embedding vector(2000),
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-large',
    embedding_dimension INTEGER DEFAULT 2000,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_semantic_user_id ON mega_agent.semantic_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_semantic_namespace ON mega_agent.semantic_memory(namespace);
CREATE INDEX IF NOT EXISTS idx_semantic_type ON mega_agent.semantic_memory(type);
CREATE INDEX IF NOT EXISTS idx_semantic_case_id ON mega_agent.semantic_memory(case_id);
CREATE INDEX IF NOT EXISTS idx_semantic_tags ON mega_agent.semantic_memory USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_semantic_created ON mega_agent.semantic_memory(created_at);
CREATE INDEX IF NOT EXISTS idx_semantic_metadata ON mega_agent.semantic_memory USING GIN(metadata_json);

-- 6. Create HNSW index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_semantic_embedding ON mega_agent.semantic_memory
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 7. Create updated_at trigger
CREATE OR REPLACE FUNCTION mega_agent.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_semantic_memory_updated_at ON mega_agent.semantic_memory;
CREATE TRIGGER update_semantic_memory_updated_at
    BEFORE UPDATE ON mega_agent.semantic_memory
    FOR EACH ROW
    EXECUTE FUNCTION mega_agent.update_updated_at_column();

-- 8. Enable Row Level Security (optional, for multi-tenant)
ALTER TABLE mega_agent.semantic_memory ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
CREATE POLICY "Service role full access" ON mega_agent.semantic_memory
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policy: Users can only see their own data (via user_id)
CREATE POLICY "Users see own data" ON mega_agent.semantic_memory
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid()::text);

-- 9. Grant permissions for PostgREST API access
GRANT SELECT, INSERT, UPDATE, DELETE ON mega_agent.semantic_memory TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON mega_agent.semantic_memory TO authenticated;

-- Verify
SELECT 'semantic_memory table created successfully' as status;
SELECT count(*) as row_count FROM mega_agent.semantic_memory;

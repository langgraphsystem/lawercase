-- Memory Schemas for MegaAgent Pro
-- Database: PostgreSQL with pgvector extension (Supabase)
-- Version: 2.0

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- Core Memory Tables
-- ============================================================================

-- Memory Records (Semantic Memory)
-- Stores processed memories with embeddings for semantic retrieval
CREATE TABLE IF NOT EXISTS memory_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT,
    case_id TEXT,
    thread_id TEXT,
    type TEXT NOT NULL DEFAULT 'semantic' CHECK (type IN ('episodic', 'semantic', 'persona', 'open_loop')),
    text TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 / Anthropic embedding dimension
    salience FLOAT CHECK (salience IS NULL OR (salience >= 0.0 AND salience <= 1.0)),
    confidence FLOAT CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    decay_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source TEXT,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for memory_records
CREATE INDEX IF NOT EXISTS idx_memory_records_user_id ON memory_records(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_records_case_id ON memory_records(case_id);
CREATE INDEX IF NOT EXISTS idx_memory_records_thread_id ON memory_records(thread_id);
CREATE INDEX IF NOT EXISTS idx_memory_records_type ON memory_records(type);
CREATE INDEX IF NOT EXISTS idx_memory_records_created_at ON memory_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_records_decay_at ON memory_records(decay_at) WHERE decay_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memory_records_tags ON memory_records USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memory_records_metadata ON memory_records USING GIN(metadata);

-- Vector similarity index (IVFFlat for large datasets)
CREATE INDEX IF NOT EXISTS idx_memory_records_embedding ON memory_records
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);


-- ============================================================================
-- Episodic Memory (Audit Events)
-- ============================================================================

-- Audit Events (Raw episodic memory)
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id TEXT,
    thread_id TEXT,
    source TEXT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT '{}',
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for audit_events
CREATE INDEX IF NOT EXISTS idx_audit_events_event_id ON audit_events(event_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_user_id ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_thread_id ON audit_events(thread_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_source ON audit_events(source);
CREATE INDEX IF NOT EXISTS idx_audit_events_action ON audit_events(action);
CREATE INDEX IF NOT EXISTS idx_audit_events_processed ON audit_events(processed) WHERE NOT processed;
CREATE INDEX IF NOT EXISTS idx_audit_events_tags ON audit_events USING GIN(tags);


-- ============================================================================
-- Working Memory (RMT Buffers)
-- ============================================================================

CREATE TABLE IF NOT EXISTS rmt_slots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    slot_value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(thread_id, slot_name)
);

CREATE INDEX IF NOT EXISTS idx_rmt_slots_thread_id ON rmt_slots(thread_id);
CREATE INDEX IF NOT EXISTS idx_rmt_slots_expires_at ON rmt_slots(expires_at) WHERE expires_at IS NOT NULL;


-- ============================================================================
-- Memory Consolidation
-- ============================================================================

CREATE TABLE IF NOT EXISTS consolidation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    deduplicated INTEGER DEFAULT 0,
    pruned INTEGER DEFAULT 0,
    merged INTEGER DEFAULT 0,
    total_after INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_consolidation_jobs_status ON consolidation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_consolidation_jobs_started_at ON consolidation_jobs(started_at DESC);


-- ============================================================================
-- Semantic Cache
-- ============================================================================

CREATE TABLE IF NOT EXISTS semantic_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_text TEXT NOT NULL,
    query_embedding vector(1536),
    response_text TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 1,
    ttl_seconds INTEGER DEFAULT 3600,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_semantic_cache_model ON semantic_cache(model);
CREATE INDEX IF NOT EXISTS idx_semantic_cache_provider ON semantic_cache(provider);
CREATE INDEX IF NOT EXISTS idx_semantic_cache_created_at ON semantic_cache(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_cache_accessed_at ON semantic_cache(accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding ON semantic_cache
    USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 50);


-- ============================================================================
-- User Personas
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_personas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL UNIQUE,
    persona_text TEXT,
    preferences JSONB DEFAULT '{}'::jsonb,
    communication_style TEXT,
    expertise_areas TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    interaction_count INTEGER DEFAULT 0,
    last_interaction_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_user_personas_user_id ON user_personas(user_id);
CREATE INDEX IF NOT EXISTS idx_user_personas_updated_at ON user_personas(updated_at DESC);


-- ============================================================================
-- Functions
-- ============================================================================

-- Search memories by semantic similarity
CREATE OR REPLACE FUNCTION search_memories(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INTEGER DEFAULT 10,
    filter_user_id TEXT DEFAULT NULL,
    filter_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    user_id TEXT,
    case_id TEXT,
    type TEXT,
    text TEXT,
    salience FLOAT,
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE,
    source TEXT,
    tags TEXT[],
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        mr.id,
        mr.user_id,
        mr.case_id,
        mr.type,
        mr.text,
        mr.salience,
        mr.confidence,
        mr.created_at,
        mr.source,
        mr.tags,
        1 - (mr.embedding <=> query_embedding) AS similarity
    FROM memory_records mr
    WHERE
        (filter_user_id IS NULL OR mr.user_id = filter_user_id)
        AND (filter_type IS NULL OR mr.type = filter_type)
        AND mr.embedding IS NOT NULL
        AND 1 - (mr.embedding <=> query_embedding) > match_threshold
        AND (mr.decay_at IS NULL OR mr.decay_at > NOW())
    ORDER BY mr.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Search semantic cache
CREATE OR REPLACE FUNCTION search_semantic_cache(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.95,
    filter_model TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    query_text TEXT,
    response_text TEXT,
    model TEXT,
    provider TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        sc.id,
        sc.query_text,
        sc.response_text,
        sc.model,
        sc.provider,
        1 - (sc.query_embedding <=> query_embedding) AS similarity
    FROM semantic_cache sc
    WHERE
        (filter_model IS NULL OR sc.model = filter_model)
        AND sc.query_embedding IS NOT NULL
        AND 1 - (sc.query_embedding <=> query_embedding) > match_threshold
        AND (sc.created_at + (sc.ttl_seconds * INTERVAL '1 second')) > NOW()
    ORDER BY sc.query_embedding <=> query_embedding
    LIMIT 1;
END;
$$;

-- Cleanup expired memories
CREATE OR REPLACE FUNCTION cleanup_expired_memories()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM memory_records
        WHERE decay_at IS NOT NULL AND decay_at < NOW()
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;

    DELETE FROM rmt_slots
    WHERE expires_at IS NOT NULL AND expires_at < NOW();

    DELETE FROM semantic_cache
    WHERE (created_at + (ttl_seconds * INTERVAL '1 second')) < NOW();

    RETURN deleted_count;
END;
$$;

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_memory_records_updated_at
    BEFORE UPDATE ON memory_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rmt_slots_updated_at
    BEFORE UPDATE ON rmt_slots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_personas_updated_at
    BEFORE UPDATE ON user_personas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- Row Level Security
-- ============================================================================

ALTER TABLE memory_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE rmt_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_personas ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own memory records"
    ON memory_records FOR SELECT
    USING (auth.uid()::text = user_id OR user_id IS NULL);

CREATE POLICY "Service role can manage all memory records"
    ON memory_records FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');


-- ============================================================================
-- Views
-- ============================================================================

CREATE OR REPLACE VIEW recent_memories AS
SELECT id, user_id, case_id, type, LEFT(text, 200) AS text_preview,
       salience, confidence, created_at, source, tags
FROM memory_records
WHERE (decay_at IS NULL OR decay_at > NOW())
ORDER BY created_at DESC LIMIT 100;

CREATE OR REPLACE VIEW memory_stats AS
SELECT type, COUNT(*) AS total_records, COUNT(DISTINCT user_id) AS unique_users,
       AVG(salience) AS avg_salience, AVG(confidence) AS avg_confidence,
       MIN(created_at) AS oldest_record, MAX(created_at) AS newest_record
FROM memory_records
WHERE (decay_at IS NULL OR decay_at > NOW())
GROUP BY type;

CREATE OR REPLACE VIEW cache_stats AS
SELECT model, provider, COUNT(*) AS total_entries, SUM(access_count) AS total_accesses,
       AVG(access_count) AS avg_access_count, SUM(cost_usd) AS total_cost_saved
FROM semantic_cache
WHERE (created_at + (ttl_seconds * INTERVAL '1 second')) > NOW()
GROUP BY model, provider;

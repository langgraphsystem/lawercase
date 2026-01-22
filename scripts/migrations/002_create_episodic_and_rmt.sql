-- Migration: Create episodic_memory and rmt_buffers tables
-- Run this in Supabase Dashboard -> SQL Editor

-- 1. Create episodic_memory table (audit trail)
CREATE TABLE IF NOT EXISTS mega_agent.episodic_memory (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Namespace / tenancy
    namespace VARCHAR(255) DEFAULT 'default',

    -- Ownership
    user_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255) NOT NULL,

    -- Event data
    source VARCHAR(100) NOT NULL CHECK (length(source) > 0),
    action VARCHAR(100) NOT NULL,
    payload JSONB DEFAULT '{}',

    -- Timestamps
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_episodic_user_id ON mega_agent.episodic_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_episodic_thread_id ON mega_agent.episodic_memory(thread_id);
CREATE INDEX IF NOT EXISTS idx_episodic_source ON mega_agent.episodic_memory(source);
CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON mega_agent.episodic_memory(timestamp);

-- RLS
ALTER TABLE mega_agent.episodic_memory ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON mega_agent.episodic_memory
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON mega_agent.episodic_memory TO service_role;


-- 2. Create rmt_buffers table (working memory)
CREATE TABLE IF NOT EXISTS mega_agent.rmt_buffers (
    buffer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Namespace / tenancy
    namespace VARCHAR(255) DEFAULT 'default',

    -- Ownership
    thread_id VARCHAR(255) NOT NULL UNIQUE,

    -- Buffer data
    slots JSONB NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(slots) = 'object'),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_rmt_thread_id ON mega_agent.rmt_buffers(thread_id);

-- Updated trigger
DROP TRIGGER IF EXISTS update_rmt_buffers_updated_at ON mega_agent.rmt_buffers;
CREATE TRIGGER update_rmt_buffers_updated_at
    BEFORE UPDATE ON mega_agent.rmt_buffers
    FOR EACH ROW
    EXECUTE FUNCTION mega_agent.update_updated_at_column();

-- RLS
ALTER TABLE mega_agent.rmt_buffers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON mega_agent.rmt_buffers
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON mega_agent.rmt_buffers TO service_role;


-- Verify
SELECT 'episodic_memory and rmt_buffers created' as status;

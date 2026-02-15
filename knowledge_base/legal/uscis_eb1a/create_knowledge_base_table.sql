-- Create knowledge_base table for RAG/vector search
-- Run this in Supabase SQL Editor

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

-- Add comment
COMMENT ON TABLE knowledge_base IS 'RAG knowledge base for document chunks and embeddings';

-- To import data, use the Supabase dashboard or:
-- INSERT INTO knowledge_base (id, content, metadata, namespace, created_at)
-- SELECT id, content, metadata, namespace, created_at::timestamptz
-- FROM json_populate_recordset(null::knowledge_base, '<json_data>');

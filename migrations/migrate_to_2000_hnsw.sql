-- Migration: Update semantic_memory to 2000 dimensions + HNSW index
-- Date: 2025-11-28
-- Reason: pgvector max dimension for HNSW/IVFFlat index is 2000
--
-- Decision: Use 2000 dimensions (max for HNSW) instead of 3072
-- OpenAI API: dimensions=2000 parameter for text-embedding-3-large
-- Trade-off: Slightly lower quality vs fast indexed search

BEGIN;

-- Step 1: Drop old embedding column
ALTER TABLE mega_agent.semantic_memory
DROP COLUMN IF EXISTS embedding CASCADE;

-- Step 2: Create new column with 2000 dimensions
ALTER TABLE mega_agent.semantic_memory
ADD COLUMN embedding vector(2000);

-- Step 3: Update defaults
ALTER TABLE mega_agent.semantic_memory
ALTER COLUMN embedding_dimension SET DEFAULT 2000;

ALTER TABLE mega_agent.semantic_memory
ALTER COLUMN embedding_model SET DEFAULT 'text-embedding-3-large';

-- Step 4: Create HNSW index
-- HNSW parameters:
--   m = 16: connections per layer (balance between speed and recall)
--   ef_construction = 64: index build accuracy
CREATE INDEX idx_semantic_memory_embedding_hnsw
ON mega_agent.semantic_memory
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMIT;

-- Verification
SELECT
    column_name,
    column_default
FROM information_schema.columns
WHERE table_schema = 'mega_agent'
AND table_name = 'semantic_memory'
AND column_name IN ('embedding_dimension', 'embedding_model');

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'mega_agent'
AND tablename = 'semantic_memory'
AND indexdef ILIKE '%hnsw%';

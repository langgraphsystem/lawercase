-- Migration: Update semantic_memory to 3072 dimensions + HNSW index
-- Date: 2025-11-28
-- Reason: Match RFE knowledge base dimension (3072) and add HNSW index
--
-- RFE Knowledge: 5626 records with 3072 dimensions (100%)
-- pgvector: 0.8.0 (supports HNSW index for >2000 dimensions)
-- IVFFlat max: 2000 dimensions (NOT suitable)

-- =============================================================================
-- PART 1: Update semantic_memory table
-- =============================================================================

BEGIN;

-- Step 1: Drop old embedding column (1 test record, safe to delete)
ALTER TABLE mega_agent.semantic_memory
DROP COLUMN IF EXISTS embedding CASCADE;

-- Step 2: Create new column with 3072 dimensions
ALTER TABLE mega_agent.semantic_memory
ADD COLUMN embedding vector(3072);

-- Step 3: Update defaults
ALTER TABLE mega_agent.semantic_memory
ALTER COLUMN embedding_dimension SET DEFAULT 3072;

ALTER TABLE mega_agent.semantic_memory
ALTER COLUMN embedding_model SET DEFAULT 'text-embedding-3-large';

-- Step 4: Create HNSW index for semantic_memory
-- HNSW (Hierarchical Navigable Small World) supports >2000 dimensions
-- Parameters:
--   m = 16: number of connections per layer (default, good balance)
--   ef_construction = 64: accuracy during index building
CREATE INDEX idx_semantic_memory_embedding_hnsw
ON mega_agent.semantic_memory
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMIT;

-- =============================================================================
-- PART 2: Create HNSW index for rfe_knowledge (PERFORMANCE BOOST!)
-- =============================================================================

-- rfe_knowledge currently has NO vector index (5626 records)
-- Vector search is slow (sequential scan) without index
-- This will significantly improve semantic search performance

BEGIN;

-- Create HNSW index for rfe_knowledge
CREATE INDEX idx_rfe_knowledge_embedding_hnsw
ON mega_agent.rfe_knowledge
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMIT;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Check semantic_memory structure
SELECT
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_schema = 'mega_agent'
AND table_name = 'semantic_memory'
AND column_name IN ('embedding', 'embedding_dimension', 'embedding_model');

-- Check indexes
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'mega_agent'
AND tablename IN ('semantic_memory', 'rfe_knowledge')
AND indexdef ILIKE '%hnsw%'
ORDER BY tablename, indexname;

-- Verify vector dimensions
SELECT
    'semantic_memory' as table_name,
    COUNT(*) as record_count,
    vector_dims(embedding) as dimension
FROM mega_agent.semantic_memory
WHERE embedding IS NOT NULL
GROUP BY vector_dims(embedding)

UNION ALL

SELECT
    'rfe_knowledge' as table_name,
    COUNT(*) as record_count,
    vector_dims(embedding) as dimension
FROM mega_agent.rfe_knowledge
WHERE embedding IS NOT NULL
GROUP BY vector_dims(embedding);

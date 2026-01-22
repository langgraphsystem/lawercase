-- Migration: Update semantic_memory table to support 3072-dimensional embeddings
-- Date: 2025-11-28
-- Reason: text-embedding-3-large default dimension is 3072, not 1536
--
-- This migration changes the vector column dimension from 1536 to 3072
-- WARNING: This will delete all existing embeddings in the table!

-- Step 1: Check current table structure
SELECT
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_schema = 'mega_agent'
AND table_name = 'semantic_memory'
AND column_name = 'embedding';

-- Step 2: Count existing records (for backup reference)
SELECT COUNT(*) as existing_records
FROM mega_agent.semantic_memory;

-- Step 3: Drop existing vector column and recreate with new dimension
-- NOTE: This will DELETE all existing embeddings!
-- If you need to preserve data, export records first and regenerate embeddings

ALTER TABLE mega_agent.semantic_memory
DROP COLUMN IF EXISTS embedding CASCADE;

ALTER TABLE mega_agent.semantic_memory
ADD COLUMN embedding vector(3072) NOT NULL DEFAULT array_fill(0, ARRAY[3072])::vector;

-- Step 4: Update default embedding_dimension value
ALTER TABLE mega_agent.semantic_memory
ALTER COLUMN embedding_dimension SET DEFAULT 3072;

-- Step 5: Update embedding_model default (optional, already set)
ALTER TABLE mega_agent.semantic_memory
ALTER COLUMN embedding_model SET DEFAULT 'text-embedding-3-large';

-- Step 6: Create index for similarity search (cosine distance)
-- Drop old index if exists
DROP INDEX IF EXISTS mega_agent.idx_semantic_memory_embedding;

-- Create new index with 3072 dimensions
CREATE INDEX IF NOT EXISTS idx_semantic_memory_embedding
ON mega_agent.semantic_memory
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Step 7: Verify changes
SELECT
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_schema = 'mega_agent'
AND table_name = 'semantic_memory'
AND column_name IN ('embedding', 'embedding_dimension', 'embedding_model');

-- Step 8: Show final table structure
\d mega_agent.semantic_memory;

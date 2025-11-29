-- Migration: Create case_intake_progress table for tracking intake questionnaire state
-- Purpose: Store per-user, per-case progress through intake blocks and questions
-- Schema: mega_agent
-- Created: 2025-11-24

-- Create case_intake_progress table
CREATE TABLE IF NOT EXISTS mega_agent.case_intake_progress (
    user_id         VARCHAR(255) NOT NULL,
    case_id         VARCHAR(255) NOT NULL,
    current_block   VARCHAR(100) NOT NULL,
    current_step    INTEGER      NOT NULL DEFAULT 0,
    completed_blocks TEXT[]      NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, case_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_case_intake_user
    ON mega_agent.case_intake_progress(user_id);

CREATE INDEX IF NOT EXISTS idx_case_intake_case
    ON mega_agent.case_intake_progress(case_id);

CREATE INDEX IF NOT EXISTS idx_case_intake_updated
    ON mega_agent.case_intake_progress(updated_at);

-- Add comments for documentation
COMMENT ON TABLE mega_agent.case_intake_progress IS
    'Tracks progress through multi-block intake questionnaire per user and case';

COMMENT ON COLUMN mega_agent.case_intake_progress.user_id IS
    'User identifier (e.g., Telegram user ID)';

COMMENT ON COLUMN mega_agent.case_intake_progress.case_id IS
    'Case UUID that this intake session belongs to';

COMMENT ON COLUMN mega_agent.case_intake_progress.current_block IS
    'ID of the current block being processed (e.g., "school", "career")';

COMMENT ON COLUMN mega_agent.case_intake_progress.current_step IS
    'Index of the next question within current_block (0-based)';

COMMENT ON COLUMN mega_agent.case_intake_progress.completed_blocks IS
    'Array of block IDs that have been fully completed';

COMMENT ON COLUMN mega_agent.case_intake_progress.updated_at IS
    'Timestamp of last progress update (auto-updated)';

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION mega_agent.update_intake_progress_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_intake_progress_timestamp
    BEFORE UPDATE ON mega_agent.case_intake_progress
    FOR EACH ROW
    EXECUTE FUNCTION mega_agent.update_intake_progress_timestamp();

-- Grant necessary permissions (adjust based on your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON mega_agent.case_intake_progress TO your_app_user;

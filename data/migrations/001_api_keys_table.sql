-- Migration: Create api_keys table for secure API key management
-- Version: 001
-- Created: 2026-01-24
-- Description: Stores hashed API keys with user associations and expiration

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash of the API key
    key_prefix VARCHAR(20) NOT NULL,       -- First 8 chars for identification
    user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'service',
    name VARCHAR(255),                      -- Human-readable name for the key
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,                 -- NULL means no expiration
    last_used_at TIMESTAMPTZ,
    usage_count INTEGER NOT NULL DEFAULT 0,
    rate_limit_per_minute INTEGER DEFAULT 60,
    allowed_ips INET[],                     -- Optional IP whitelist
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;

-- Create function to update last_used_at and usage_count
CREATE OR REPLACE FUNCTION update_api_key_usage()
RETURNS TRIGGER AS $$
BEGIN
    -- This trigger would be called by application code via RPC
    UPDATE api_keys
    SET last_used_at = NOW(),
        usage_count = usage_count + 1
    WHERE id = NEW.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create RPC function for updating key usage (to be called from application)
CREATE OR REPLACE FUNCTION record_api_key_usage(p_key_hash VARCHAR(64))
RETURNS VOID AS $$
BEGIN
    UPDATE api_keys
    SET last_used_at = NOW(),
        usage_count = usage_count + 1
    WHERE key_hash = p_key_hash AND is_active = TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create RPC function for checking rate limits
CREATE OR REPLACE FUNCTION check_api_key_rate_limit(p_key_hash VARCHAR(64))
RETURNS TABLE(
    allowed BOOLEAN,
    current_usage INTEGER,
    limit_per_minute INTEGER
) AS $$
DECLARE
    v_rate_limit INTEGER;
    v_recent_usage INTEGER;
BEGIN
    -- Get the rate limit for this key
    SELECT rate_limit_per_minute INTO v_rate_limit
    FROM api_keys
    WHERE key_hash = p_key_hash AND is_active = TRUE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 0, 0;
        RETURN;
    END IF;

    -- Count recent usage (would need a separate usage log table for accurate tracking)
    -- For now, return a placeholder
    v_recent_usage := 0;

    RETURN QUERY SELECT
        (v_recent_usage < COALESCE(v_rate_limit, 60)),
        v_recent_usage,
        COALESCE(v_rate_limit, 60);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Row Level Security (RLS)
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Policy: Only allow service role to manage api_keys
CREATE POLICY api_keys_service_policy ON api_keys
    FOR ALL
    USING (auth.role() = 'service_role');

-- Policy: Allow authenticated users to view their own keys (limited columns)
CREATE POLICY api_keys_user_view_policy ON api_keys
    FOR SELECT
    USING (
        auth.uid()::text = user_id
        OR auth.role() = 'service_role'
    );

-- Comment on table
COMMENT ON TABLE api_keys IS 'Stores hashed API keys for authentication. Keys are never stored in plaintext.';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the full API key';
COMMENT ON COLUMN api_keys.key_prefix IS 'First 8 characters of the key for identification in UI';
COMMENT ON COLUMN api_keys.expires_at IS 'NULL means the key never expires';
COMMENT ON COLUMN api_keys.allowed_ips IS 'Optional whitelist of allowed IP addresses';

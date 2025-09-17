-- Initial schema for mega_agent_pro persistence

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  external_id VARCHAR(64) UNIQUE,
  role VARCHAR(32) DEFAULT 'lawyer',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cases (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  title VARCHAR(255) NOT NULL,
  status VARCHAR(32) DEFAULT 'open',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  case_id INTEGER REFERENCES cases(id) ON DELETE SET NULL,
  external_id VARCHAR(64),
  title VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_documents_external_id ON documents(external_id);

CREATE TABLE IF NOT EXISTS chunks (
  id SERIAL PRIMARY KEY,
  document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
  chunk_id VARCHAR(64) NOT NULL,
  text TEXT NOT NULL,
  score DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_id ON chunks(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);

CREATE TABLE IF NOT EXISTS case_items (
  id SERIAL PRIMARY KEY,
  case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
  item_type VARCHAR(32) NOT NULL,
  item_id VARCHAR(64) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id SERIAL PRIMARY KEY,
  case_id INTEGER REFERENCES cases(id) ON DELETE SET NULL,
  sender VARCHAR(64) NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_keys (
  id SERIAL PRIMARY KEY,
  key_id VARCHAR(64) UNIQUE NOT NULL,
  key_hash VARCHAR(128) NOT NULL,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  name VARCHAR(128) NOT NULL,
  permissions TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  expires_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id SERIAL PRIMARY KEY,
  event_id VARCHAR(64) NOT NULL,
  user_id VARCHAR(64),
  source VARCHAR(64) NOT NULL,
  action VARCHAR(64) NOT NULL,
  payload TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);


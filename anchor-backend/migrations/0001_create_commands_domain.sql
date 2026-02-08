CREATE TABLE IF NOT EXISTS commands_domain (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  result JSONB,
  error TEXT,
  attempt INT NOT NULL DEFAULT 0,
  locked_by TEXT,
  locked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_commands_domain_status_created
  ON commands_domain (status, created_at);

-- Ops state store: aggregated cache + history
CREATE TABLE IF NOT EXISTS ops_state (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops_state_history (
  id BIGSERIAL PRIMARY KEY,
  key TEXT NOT NULL,
  value JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ops_state_history_created
  ON ops_state_history (created_at DESC);

-- Risk state: single-row ledger for current exposure
CREATE TABLE IF NOT EXISTS risk_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  current_exposure_usd NUMERIC NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed the single row (idempotent)
INSERT INTO risk_state (id, current_exposure_usd)
VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;

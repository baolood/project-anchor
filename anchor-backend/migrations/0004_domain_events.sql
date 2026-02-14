-- Append-only audit trail for domain command lifecycle (PICKED, ACTION_OK, ACTION_FAIL, MARK_DONE, MARK_FAILED, RETRY, EXCEPTION)
CREATE TABLE IF NOT EXISTS domain_events (
  id BIGSERIAL PRIMARY KEY,
  command_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  attempt INT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_domain_events_command_created
  ON domain_events (command_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_domain_events_type_created
  ON domain_events (event_type, created_at DESC);

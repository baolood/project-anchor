-- Phase 3.7: durable risk_state table
CREATE TABLE IF NOT EXISTS risk_state (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- optional audit/history table (append-only)
CREATE TABLE IF NOT EXISTS risk_state_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  key TEXT NOT NULL,
  value JSONB NOT NULL,
  actor TEXT,
  note TEXT,
  ts TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

#!/usr/bin/env bash
# Apply risk_state migration to anchor database.
# Run from anchor-backend: bash scripts/apply_risk_state_migration.sh
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

echo "===== APPLY ATOMIC RISK LEDGER MIGRATION ====="

docker compose exec -T postgres env PGPASSWORD=anchor psql -U anchor -d anchor <<'SQL'
BEGIN;

-- 1) Create risk_state table (single-row ledger)
CREATE TABLE IF NOT EXISTS risk_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  current_exposure_usd NUMERIC NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2) Insert singleton row if not exists
INSERT INTO risk_state (id, current_exposure_usd)
VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;

COMMIT;
SQL

echo "===== VERIFY TABLE ====="
docker compose exec -T postgres env PGPASSWORD=anchor psql -U anchor -d anchor -c \
  "SELECT id, current_exposure_usd, updated_at FROM risk_state;"

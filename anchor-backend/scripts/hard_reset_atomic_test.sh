#!/usr/bin/env bash
# Hard reset, rebuild with atomic mode, run 50 concurrent quotes test.
# Usage: cd anchor-backend && bash scripts/hard_reset_atomic_test.sh
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

echo "===== HARD RESET ====="
docker compose down -v
docker system prune -f

echo "===== REBUILD WITH ATOMIC MODE ====="
CAPITAL_USD=1000 \
MAX_SINGLE_TRADE_RISK_PCT=100 \
MAX_NET_EXPOSURE_PCT=30 \
RISK_HARD_LIMITS_DISABLE=0 \
RISK_EXPOSURE_ATOMIC=1 \
  docker compose up -d --build

sleep 5

echo "===== APPLY MIGRATIONS (fresh DB) ====="
for f in $(ls migrations/*.sql 2>/dev/null | sort); do
  echo "[migrate] applying $f"
  docker compose exec -T postgres env PGPASSWORD=anchor psql -U anchor -d anchor < "$f" || true
done
sleep 2

echo "===== VERIFY WORKER ENV ====="
docker compose exec worker env 2>/dev/null | grep -E '^RISK|^CAPITAL|^DATABASE' || true

echo "===== VERIFY risk_state EXISTS ====="
docker compose exec -T postgres env PGPASSWORD=anchor psql -U anchor -d anchor -c "SELECT * FROM risk_state;" || echo "(risk_state check failed)"

echo "===== RESET COMMANDS ====="
curl -s -X POST http://127.0.0.1:8000/ops/dev/reset-pending-domain-commands > /dev/null || true

echo "===== RUN 50 CONCURRENT QUOTES ====="
for i in {1..50}; do
  curl -s -X POST http://127.0.0.1:8000/domain-commands/quote \
    -H "Content-Type: application/json" \
    -d '{"symbol":"BTCUSDT","notional":150,"stop_loss":100}' &
done
wait
sleep 8

echo "===== RESULT ====="
DONE=$(curl -s "http://127.0.0.1:8000/domain-commands?limit=60" | jq '[.[] | select(.status=="DONE")] | length')
FAILED=$(curl -s "http://127.0.0.1:8000/domain-commands?limit=60" | jq '[.[] | select(.status=="FAILED")] | length')
echo "DONE=$DONE"
echo "FAILED=$FAILED"

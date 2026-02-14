#!/usr/bin/env bash
# Concurrent test: 10 QUOTE with notional 150 (blocked by single-trade 15% > 0.5%).
# Requires: worker with RISK_HARD_LIMITS_DISABLE=0, CAPITAL_USD=1000.
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

BASE="${BASE:-http://127.0.0.1:8000}"

echo "===== RESET PENDING ====="
curl -s -X POST "$BASE/ops/dev/reset-pending-domain-commands" > /dev/null

echo "===== RESTART WORKER WITH HARD LIMITS ====="
cd anchor-backend
docker compose stop worker 2>/dev/null || true
sleep 2
CAPITAL_USD=1000 \
MAX_NET_EXPOSURE_PCT=30 \
RISK_HARD_LIMITS_DISABLE=0 \
  docker compose up -d worker
sleep 5
cd ..

echo "===== START CONCURRENT SUBMISSIONS ====="

for i in {1..10}; do
  curl -s -X POST "$BASE/domain-commands/quote" \
    -H "Content-Type: application/json" \
    -d '{"symbol":"BTCUSDT","notional":150,"stop_loss":100}' &
done

wait

echo "===== WAIT WORKER ====="
sleep 8

echo "===== RESULT SUMMARY ====="
curl -s "$BASE/domain-commands?limit=50" | \
  jq -r '.[] | "\(.id) \(.status) \(.error // "—") \(.payload.notional // "—")"' | sort

echo ""
echo "===== DONE COUNT ====="
curl -s "$BASE/domain-commands?limit=50" | jq '[.[] | select(.status=="DONE")] | length'

echo "===== FAILED COUNT ====="
curl -s "$BASE/domain-commands?limit=50" | jq '[.[] | select(.status=="FAILED")] | length'

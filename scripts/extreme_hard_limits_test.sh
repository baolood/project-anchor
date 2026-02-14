#!/usr/bin/env bash
# Extreme concurrent test: 20 over-leverage + 20 compliant QUOTE commands.
# Requires: worker with RISK_HARD_LIMITS_DISABLE=0, CAPITAL_USD=1000.
# Run from project root: bash scripts/extreme_hard_limits_test.sh
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

BASE="${BASE:-http://127.0.0.1:8000}"
CONSOLE="${CONSOLE:-http://127.0.0.1:3000}"

echo "===== RESET PENDING ====="
curl -s -X POST "$BASE/ops/dev/reset-pending-domain-commands" | head -1

echo "===== EXTREME TEST START ====="

# 1) 20 over-leverage QUOTE (notional 100000, capital 1000 -> blocked)
for i in {1..20}; do
  curl -s -X POST "$BASE/domain-commands/quote" \
    -H "Content-Type: application/json" \
    -d '{"symbol":"BTCUSDT","notional":100000,"stop_loss":100}' &
done

# 2) 20 compliant small QUOTE (notional 5, stop_loss -> pass)
for i in {1..20}; do
  curl -s -X POST "$BASE/domain-commands/quote" \
    -H "Content-Type: application/json" \
    -d '{"symbol":"BTCUSDT","notional":5,"stop_loss":100}' &
done

wait

echo "===== WAITING FOR WORKER ====="
sleep 10

echo "===== RESULT SUMMARY ====="
curl -s "$BASE/domain-commands?limit=100" | jq -r '.[] | "\(.id) \(.status) \(.error // "—")"' | sort

echo ""
echo "===== COUNTS ====="
total=$(curl -s "$BASE/domain-commands?limit=200" | jq 'length')
failed=$(curl -s "$BASE/domain-commands?limit=200" | jq '[.[] | select(.status=="FAILED")] | length')
done_count=$(curl -s "$BASE/domain-commands?limit=200" | jq '[.[] | select(.status=="DONE")] | length')
pending=$(curl -s "$BASE/domain-commands?limit=200" | jq '[.[] | select(.status=="PENDING")] | length')
echo "Total: $total | FAILED: $failed | DONE: $done_count | PENDING: $pending"

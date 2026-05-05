#!/usr/bin/env bash
# Enable atomic exposure mode (risk_state ledger). Run migration first.
# Usage: bash scripts/enable_atomic_exposure.sh
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

echo "===== PATCH HARD LIMITS TO ATOMIC MODE ====="
echo "(atomic_exposure_guard.py + hard_limits integration already in place)"
echo ""

echo "===== REBUILD & RESTART WORKER ====="
docker compose stop worker 2>/dev/null || true
sleep 2

CAPITAL_USD=1000 \
MAX_SINGLE_TRADE_RISK_PCT=100 \
MAX_NET_EXPOSURE_PCT=30 \
RISK_HARD_LIMITS_DISABLE=0 \
RISK_EXPOSURE_ATOMIC=1 \
  docker compose up -d --build worker

sleep 5
echo "===== ATOMIC MODE READY ====="

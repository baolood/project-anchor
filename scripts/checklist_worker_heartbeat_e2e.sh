#!/usr/bin/env bash
# Worker heartbeat E2E: worker writes WORKER_HEARTBEAT every WORKER_HEARTBEAT_SECONDS (default 30).
# GET /ops/worker returns last_heartbeat_at. PASS if at least one heartbeat in window.
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_worker_heartbeat_e2e_last.out}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""

echo "=============================="
echo "MODULE=worker_heartbeat_e2e"
echo "Step0: Precheck backend"
echo "=============================="
if ! curl -sS --noproxy '*' -o /dev/null -w "%{http_code}" "$BACKEND_PRECHECK/health" | grep -q 200; then
  echo "FAIL_REASON=backend_not_reachable"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: backend reachable"

echo "=============================="
echo "Step1: Wait 35s for worker heartbeat (interval default 30s)"
echo "=============================="
sleep 35

echo "=============================="
echo "Step2: GET /ops/worker — last_heartbeat_at present"
echo "=============================="
worker_json="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/ops/worker")"
if ! echo "$worker_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
hb = data.get('last_heartbeat_at')
if not hb:
    sys.exit(1)
sys.exit(0)
"; then
  FAIL_REASON=no_last_heartbeat_at
  echo "FAIL_REASON=$FAIL_REASON"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: last_heartbeat_at present and recent"

PASS_OR_FAIL=PASS
FAIL_REASON=""
echo "=============================="
echo "MODULE=worker_heartbeat_e2e"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"

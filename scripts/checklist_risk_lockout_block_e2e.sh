#!/usr/bin/env bash
# Risk Lockout Block E2E: lockout active -> risk commands blocked (RISK_LOCKOUT_ACTIVE), allowlist (NOOP) passes.
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_risk_lockout_block_e2e_last.out}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"
ANCHOR_BACKEND_DIR="${ANCHOR_BACKEND_DIR:-$(cd "$(dirname "$0")/.." && pwd)/anchor-backend}"
BACKEND_DIR="${BACKEND_DIR:-$ANCHOR_BACKEND_DIR}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""
BLOCKED_CMD_FAIL_REASON=NO
ALLOWLIST_NOOP_PASS=NO

echo "=============================="
echo "MODULE=risk_lockout_block_e2e"
echo "Step0: Ensure backend + kill switch OFF, restart worker with RISK_LOCKOUT_CONSEC_LOSSES=1"
echo "=============================="
if ! curl -sS --noproxy '*' -o /dev/null -w "%{http_code}" "$BACKEND_PRECHECK/health" | grep -q 200; then
  echo "FAIL_REASON=backend_not_reachable" > "$OUT"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL" >> "$OUT"
  cat "$OUT"
  exit 1
fi
curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":false}' "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
cd "$ANCHOR_BACKEND_DIR"
# Clear Redis "lockout cleared" key so this run tests real lockout (not bypassed by previous cleanup)
docker compose -f "$BACKEND_DIR/docker-compose.yml" exec -T redis redis-cli DEL anchor:risk_lockout_cleared >/dev/null 2>&1 || true
docker compose -f "$BACKEND_DIR/docker-compose.yml" stop worker 2>/dev/null || true
sleep 2
RISK_LOCKOUT_CONSEC_LOSSES=1 RISK_LOCKOUT_DISABLE=0 docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker
sleep 5
echo "OK: worker restarted with RISK_LOCKOUT_CONSEC_LOSSES=1"

echo "=============================="
echo "Step1: Create one FAIL command to trigger MARK_FAILED (lockout)"
echo "=============================="
fail_resp="$(curl -sS --noproxy '*' -X POST "$BACKEND_PRECHECK/domain-commands/fail")"
FAIL_ID="$(echo "$fail_resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")"
if [ -z "$FAIL_ID" ]; then
  FAIL_REASON=fail_post_failed
  echo "FAIL_REASON=$FAIL_REASON" > "$OUT"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL" >> "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "FAIL_ID=$FAIL_ID"
for i in $(seq 1 15); do
  status="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/$FAIL_ID" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  [ "$status" = "FAILED" ] && break
  sleep 1
done
echo "OK: fail command processed (status=$status)"

echo "=============================="
echo "Step2: Create QUOTE (non-allowlist) -> expect FAILED with RISK_LOCKOUT_ACTIVE"
echo "=============================="
quote_resp="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"symbol":"BTCUSDT","side":"BUY","notional":10}' "$BACKEND_PRECHECK/domain-commands/quote")"
QUOTE_ID="$(echo "$quote_resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")"
if [ -z "$QUOTE_ID" ]; then
  FAIL_REASON=quote_post_failed
  echo "FAIL_REASON=$FAIL_REASON" > "$OUT"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL" >> "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "QUOTE_ID=$QUOTE_ID"
for i in $(seq 1 35); do
  detail="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/$QUOTE_ID" 2>/dev/null)"
  status="$(echo "$detail" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  error="$(echo "$detail" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null || echo "")"
  if [ "$status" = "FAILED" ] && [ -n "$error" ] && echo "$error" | grep -q "RISK_LOCKOUT"; then
    BLOCKED_CMD_FAIL_REASON=YES
    break
  fi
  if [ "$status" = "DONE" ]; then
    echo "WARN: QUOTE got DONE (lockout did not block)"
    break
  fi
  sleep 1
done
if [ "$BLOCKED_CMD_FAIL_REASON" != "YES" ]; then
  FAIL_REASON=quote_not_blocked
  {
    echo "MODULE=risk_lockout_block_e2e"
    echo "BLOCKED_CMD_FAIL_REASON=$BLOCKED_CMD_FAIL_REASON"
    echo "ALLOWLIST_NOOP_PASS=$ALLOWLIST_NOOP_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "OK: QUOTE blocked with RISK_LOCKOUT_ACTIVE"

echo "=============================="
echo "Step3: Create NOOP (allowlist) -> expect DONE"
echo "=============================="
noop_resp="$(curl -sS --noproxy '*' -X POST "$BACKEND_PRECHECK/domain-commands/noop")"
NOOP_ID="$(echo "$noop_resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")"
if [ -z "$NOOP_ID" ]; then
  FAIL_REASON=noop_post_failed
  {
    echo "MODULE=risk_lockout_block_e2e"
    echo "BLOCKED_CMD_FAIL_REASON=$BLOCKED_CMD_FAIL_REASON"
    echo "ALLOWLIST_NOOP_PASS=$ALLOWLIST_NOOP_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
for i in $(seq 1 15); do
  status="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/$NOOP_ID" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  [ "$status" = "DONE" ] && ALLOWLIST_NOOP_PASS=YES && break
  sleep 1
done
if [ "$ALLOWLIST_NOOP_PASS" != "YES" ]; then
  FAIL_REASON=noop_not_done
  {
    echo "MODULE=risk_lockout_block_e2e"
    echo "BLOCKED_CMD_FAIL_REASON=$BLOCKED_CMD_FAIL_REASON"
    echo "ALLOWLIST_NOOP_PASS=$ALLOWLIST_NOOP_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "OK: NOOP passed (DONE)"

echo "=============================="
echo "Cleanup: Restore worker (default env)"
echo "=============================="
docker compose -f "$BACKEND_DIR/docker-compose.yml" stop worker 2>/dev/null || true
docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
curl -sS --noproxy '*' -X POST "$BACKEND_PRECHECK/risk/lockout/clear" >/dev/null || true
sleep 2
echo "OK: cleanup done"

PASS_OR_FAIL=PASS
FAIL_REASON=""
{
  echo "MODULE=risk_lockout_block_e2e"
  echo "BLOCKED_CMD_FAIL_REASON=$BLOCKED_CMD_FAIL_REASON"
  echo "ALLOWLIST_NOOP_PASS=$ALLOWLIST_NOOP_PASS"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  echo "CHECKLIST_RISK_LOCKOUT_BLOCK_OUT=$OUT"
} > "$OUT"
cat "$OUT"
exit 0

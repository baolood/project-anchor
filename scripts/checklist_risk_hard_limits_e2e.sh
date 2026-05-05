#!/usr/bin/env bash
# Risk Hard Limits E2E: QUOTE commands blocked by RISK_HARD_LIMITS when exceeding limits.
# Step1: over-leverage -> FAIL
# Step2: over-exposure -> FAIL
# Step3: no stop -> FAIL
# Step4: compliant -> PASS
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_risk_hard_limits_e2e_last.out}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"
ANCHOR_BACKEND_DIR="${ANCHOR_BACKEND_DIR:-$(cd "$(dirname "$0")/.." && pwd)/anchor-backend}"
BACKEND_DIR="${BACKEND_DIR:-$ANCHOR_BACKEND_DIR}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""
OVER_LEV_FAIL=NO
OVER_EXPOSURE_FAIL=NO
NO_STOP_FAIL=NO
COMPLIANT_PASS=NO

echo "=============================="
echo "MODULE=risk_hard_limits_e2e"
echo "Step0: Ensure backend up, restart worker with hard limits enabled"
echo "=============================="
if ! curl -sS --noproxy '*' -o /dev/null -w "%{http_code}" "$BACKEND_PRECHECK/health" | grep -q 200; then
  echo "FAIL_REASON=backend_not_reachable" > "$OUT"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL" >> "$OUT"
  cat "$OUT"
  exit 1
fi
cd "$ANCHOR_BACKEND_DIR"
docker compose -f "$BACKEND_DIR/docker-compose.yml" stop worker 2>/dev/null || true
sleep 2
# CAPITAL_USD=1000, limits: single 0.5%, exposure 30%, leverage 5. Hard limits ON.
export CAPITAL_USD=1000
export MAX_SINGLE_TRADE_RISK_PCT=0.5
export MAX_NET_EXPOSURE_PCT=30
export MAX_LEVERAGE=5
export MAX_DAILY_DRAWDOWN_PCT=3
export RISK_HARD_LIMITS_DISABLE=0
export RISK_EXPOSURE_ATOMIC=1
docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker
sleep 5
echo "OK: worker restarted with hard limits"
# Clear any PENDING from previous tests so our quotes are picked first
curl -sS --noproxy '*' -X POST "$BACKEND_PRECHECK/ops/dev/reset-pending-domain-commands" >/dev/null || true
sleep 2

echo "=============================="
echo "Step1: QUOTE over-leverage (notional 6000, capital 1000 -> 600%% single trade > 0.5%%) -> expect FAILED"
echo "=============================="
r1="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","notional":6000,"stop_loss":100}' "$BACKEND_PRECHECK/domain-commands/quote")"
ID1="$(echo "$r1" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")"
if [ -z "$ID1" ]; then
  FAIL_REASON=quote1_post_failed
  echo "FAIL_REASON=$FAIL_REASON" > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
for i in $(seq 1 30); do
  detail="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/$ID1" 2>/dev/null)"
  status="$(echo "$detail" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  error="$(echo "$detail" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null || echo "")"
  if [ "$status" = "FAILED" ] && [ -n "$error" ] && (echo "$error" | grep -q "LEVERAGE_EXCEEDED" || echo "$error" | grep -q "SINGLE_TRADE_RISK_EXCEEDED"); then
    OVER_LEV_FAIL=YES
    break
  fi
  if [ "$status" = "DONE" ]; then
    echo "WARN: over-leverage QUOTE got DONE (hard limits did not block)"
    break
  fi
  sleep 1
done
if [ "$OVER_LEV_FAIL" != "YES" ]; then
  FAIL_REASON=over_leverage_not_blocked
  {
    echo "MODULE=risk_hard_limits_e2e"
    echo "OVER_LEV_FAIL=$OVER_LEV_FAIL"
    echo "OVER_EXPOSURE_FAIL=$OVER_EXPOSURE_FAIL"
    echo "NO_STOP_FAIL=$NO_STOP_FAIL"
    echo "COMPLIANT_PASS=$COMPLIANT_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "OK: over-leverage blocked (SINGLE_TRADE_RISK or LEVERAGE_EXCEEDED)"

echo "=============================="
echo "Step2: QUOTE over-exposure (notional 400, capital 1000 -> 40% > 30%) -> expect FAILED"
echo "=============================="
r2="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","notional":400,"stop_loss":100}' "$BACKEND_PRECHECK/domain-commands/quote")"
ID2="$(echo "$r2" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")"
if [ -z "$ID2" ]; then
  FAIL_REASON=quote2_post_failed
  {
    echo "MODULE=risk_hard_limits_e2e"
    echo "OVER_LEV_FAIL=$OVER_LEV_FAIL"
    echo "OVER_EXPOSURE_FAIL=$OVER_EXPOSURE_FAIL"
    echo "NO_STOP_FAIL=$NO_STOP_FAIL"
    echo "COMPLIANT_PASS=$COMPLIANT_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
for i in $(seq 1 30); do
  detail="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/$ID2" 2>/dev/null)"
  status="$(echo "$detail" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  error="$(echo "$detail" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null || echo "")"
  if [ "$status" = "FAILED" ] && [ -n "$error" ] && (echo "$error" | grep -q "NET_EXPOSURE_EXCEEDED" || echo "$error" | grep -q "SINGLE_TRADE_RISK_EXCEEDED" || echo "$error" | grep -q "LEVERAGE_EXCEEDED"); then
    OVER_EXPOSURE_FAIL=YES
    break
  fi
  if [ "$status" = "DONE" ]; then
    echo "WARN: over-exposure QUOTE got DONE"
    break
  fi
  sleep 1
done
if [ "$OVER_EXPOSURE_FAIL" != "YES" ]; then
  FAIL_REASON=over_exposure_not_blocked
  {
    echo "MODULE=risk_hard_limits_e2e"
    echo "OVER_LEV_FAIL=$OVER_LEV_FAIL"
    echo "OVER_EXPOSURE_FAIL=$OVER_EXPOSURE_FAIL"
    echo "NO_STOP_FAIL=$NO_STOP_FAIL"
    echo "COMPLIANT_PASS=$COMPLIANT_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "OK: over-exposure blocked (NET_EXPOSURE or SINGLE_TRADE_RISK or LEVERAGE)"

echo "=============================="
echo "Step3: QUOTE no stop (notional 5, no stop_loss) -> expect FAILED"
echo "=============================="
r3="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","notional":5}' "$BACKEND_PRECHECK/domain-commands/quote")"
ID3="$(echo "$r3" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")"
if [ -z "$ID3" ]; then
  FAIL_REASON=quote3_post_failed
  {
    echo "MODULE=risk_hard_limits_e2e"
    echo "OVER_LEV_FAIL=$OVER_LEV_FAIL"
    echo "OVER_EXPOSURE_FAIL=$OVER_EXPOSURE_FAIL"
    echo "NO_STOP_FAIL=$NO_STOP_FAIL"
    echo "COMPLIANT_PASS=$COMPLIANT_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
for i in $(seq 1 30); do
  detail="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/$ID3" 2>/dev/null)"
  status="$(echo "$detail" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  error="$(echo "$detail" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null || echo "")"
  if [ "$status" = "FAILED" ] && [ -n "$error" ] && echo "$error" | grep -q "STOP_REQUIRED"; then
    NO_STOP_FAIL=YES
    break
  fi
  if [ "$status" = "DONE" ]; then
    echo "WARN: no-stop QUOTE got DONE"
    break
  fi
  sleep 1
done
if [ "$NO_STOP_FAIL" != "YES" ]; then
  FAIL_REASON=no_stop_not_blocked
  {
    echo "MODULE=risk_hard_limits_e2e"
    echo "OVER_LEV_FAIL=$OVER_LEV_FAIL"
    echo "OVER_EXPOSURE_FAIL=$OVER_EXPOSURE_FAIL"
    echo "NO_STOP_FAIL=$NO_STOP_FAIL"
    echo "COMPLIANT_PASS=$COMPLIANT_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "OK: no-stop blocked (STOP_REQUIRED)"

pre_step_clean() {
  curl -sS --noproxy '*' -X POST "$BACKEND_PRECHECK/ops/dev/reset-pending-domain-commands" >/dev/null || true
  docker compose -f "$BACKEND_DIR/docker-compose.yml" exec -T postgres psql -U anchor -d anchor -c \
    "UPDATE risk_state SET current_exposure_usd=0, updated_at=NOW() WHERE id=1;" >/dev/null 2>&1 || true
  sleep 2
}
pre_step_clean

echo "=============================="
echo "Step4: QUOTE compliant (notional 5, stop_loss 100) -> expect DONE"
echo "=============================="
r4="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","notional":5,"stop_loss":100}' "$BACKEND_PRECHECK/domain-commands/quote")"
ID4="$(echo "$r4" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")"
if [ -z "$ID4" ]; then
  FAIL_REASON=quote4_post_failed
  {
    echo "MODULE=risk_hard_limits_e2e"
    echo "OVER_LEV_FAIL=$OVER_LEV_FAIL"
    echo "OVER_EXPOSURE_FAIL=$OVER_EXPOSURE_FAIL"
    echo "NO_STOP_FAIL=$NO_STOP_FAIL"
    echo "COMPLIANT_PASS=$COMPLIANT_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
for i in $(seq 1 30); do
  status="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/$ID4" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  [ "$status" = "DONE" ] && COMPLIANT_PASS=YES && break
  sleep 1
done
if [ "$COMPLIANT_PASS" != "YES" ]; then
  FAIL_REASON=compliant_not_done
  {
    echo "MODULE=risk_hard_limits_e2e"
    echo "OVER_LEV_FAIL=$OVER_LEV_FAIL"
    echo "OVER_EXPOSURE_FAIL=$OVER_EXPOSURE_FAIL"
    echo "NO_STOP_FAIL=$NO_STOP_FAIL"
    echo "COMPLIANT_PASS=$COMPLIANT_PASS"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "OK: compliant QUOTE passed (DONE)"

echo "=============================="
echo "Cleanup: Restore worker (default env)"
echo "=============================="
docker compose -f "$BACKEND_DIR/docker-compose.yml" stop worker 2>/dev/null || true
docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
sleep 2
echo "OK: cleanup done"

PASS_OR_FAIL=PASS
FAIL_REASON=""
{
  echo "MODULE=risk_hard_limits_e2e"
  echo "OVER_LEV_FAIL=$OVER_LEV_FAIL"
  echo "OVER_EXPOSURE_FAIL=$OVER_EXPOSURE_FAIL"
  echo "NO_STOP_FAIL=$NO_STOP_FAIL"
  echo "COMPLIANT_PASS=$COMPLIANT_PASS"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  echo "CHECKLIST_RISK_HARD_LIMITS_OUT=$OUT"
} > "$OUT"
cat "$OUT"
exit 0

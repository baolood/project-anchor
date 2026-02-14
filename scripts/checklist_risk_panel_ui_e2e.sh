#!/usr/bin/env bash
# Risk Panel UI E2E: /risk page reachable + proxy /api/proxy/risk/state returns 200 + required keys.
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_risk_panel_ui_e2e_last.out}"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""
PAGE_HTTP_STATUS=""
STATE_HTTP_STATUS=""
HAS_DAILY_LOSS_BUDGET_PCT=NO
HAS_DAILY_LOSS_BUDGET_USD=NO
HAS_TODAY_PNL=NO
HAS_TODAY_LOSS_PCT=NO
HAS_CONSECUTIVE_LOSSES=NO
HAS_NET_EXPOSURE_USD=NO
HAS_POSITIONS_COUNT=NO
HAS_LOCKOUT_ENABLED=NO
HAS_LOCKOUT_REASON=NO
HAS_LOCKOUT_UNTIL=NO

echo "=============================="
echo "MODULE=risk_panel_ui_e2e"
echo "Step0: GET CONSOLE_URL/risk -> 200"
echo "=============================="
page_code="$(curl -sS -o /dev/null -w "%{http_code}" --noproxy '*' "$CONSOLE_URL/risk" 2>/dev/null || echo "000")"
PAGE_HTTP_STATUS="${page_code}"

if [ "$PAGE_HTTP_STATUS" != "200" ]; then
  FAIL_REASON=risk_page_http_not_200
  {
    echo "MODULE=risk_panel_ui_e2e"
    echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
    echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
    echo "HAS_DAILY_LOSS_BUDGET_PCT=$HAS_DAILY_LOSS_BUDGET_PCT"
    echo "HAS_DAILY_LOSS_BUDGET_USD=$HAS_DAILY_LOSS_BUDGET_USD"
    echo "HAS_TODAY_PNL=$HAS_TODAY_PNL"
    echo "HAS_TODAY_LOSS_PCT=$HAS_TODAY_LOSS_PCT"
    echo "HAS_CONSECUTIVE_LOSSES=$HAS_CONSECUTIVE_LOSSES"
    echo "HAS_NET_EXPOSURE_USD=$HAS_NET_EXPOSURE_USD"
    echo "HAS_POSITIONS_COUNT=$HAS_POSITIONS_COUNT"
    echo "HAS_LOCKOUT_ENABLED=$HAS_LOCKOUT_ENABLED"
    echo "HAS_LOCKOUT_REASON=$HAS_LOCKOUT_REASON"
    echo "HAS_LOCKOUT_UNTIL=$HAS_LOCKOUT_UNTIL"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi
echo "OK: /risk -> 200"

echo "=============================="
echo "Step1: GET CONSOLE_URL/api/proxy/risk/state -> 200 and required keys present"
echo "=============================="
state_resp="$(curl -sS --noproxy '*' -w "\n%{http_code}" "$CONSOLE_URL/api/proxy/risk/state")"
STATE_HTTP_STATUS="$(echo "$state_resp" | tail -1)"
state_body="$(echo "$state_resp" | sed '$d')"

if [ "$STATE_HTTP_STATUS" != "200" ]; then
  FAIL_REASON=risk_state_proxy_http_not_200
  {
    echo "MODULE=risk_panel_ui_e2e"
    echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
    echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
    echo "HAS_DAILY_LOSS_BUDGET_PCT=$HAS_DAILY_LOSS_BUDGET_PCT"
    echo "HAS_DAILY_LOSS_BUDGET_USD=$HAS_DAILY_LOSS_BUDGET_USD"
    echo "HAS_TODAY_PNL=$HAS_TODAY_PNL"
    echo "HAS_TODAY_LOSS_PCT=$HAS_TODAY_LOSS_PCT"
    echo "HAS_CONSECUTIVE_LOSSES=$HAS_CONSECUTIVE_LOSSES"
    echo "HAS_NET_EXPOSURE_USD=$HAS_NET_EXPOSURE_USD"
    echo "HAS_POSITIONS_COUNT=$HAS_POSITIONS_COUNT"
    echo "HAS_LOCKOUT_ENABLED=$HAS_LOCKOUT_ENABLED"
    echo "HAS_LOCKOUT_REASON=$HAS_LOCKOUT_REASON"
    echo "HAS_LOCKOUT_UNTIL=$HAS_LOCKOUT_UNTIL"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi

has_keys="$(echo "$state_body" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    req = ['daily_loss_budget_pct', 'daily_loss_budget_usd', 'today_pnl', 'today_loss_pct',
           'consecutive_losses', 'net_exposure_usd', 'positions_count',
           'lockout_enabled', 'lockout_reason', 'lockout_until', 'generated_at']
    for k in req:
        if k not in d:
            print('missing:' + k)
            sys.exit(1)
    # daily_loss_budget_pct non-null (must be number)
    v = d.get('daily_loss_budget_pct')
    if v is None:
        print('daily_loss_budget_pct_null')
        sys.exit(1)
    if not isinstance(v, (int, float)):
        print('daily_loss_budget_pct_not_number')
        sys.exit(1)
    # lockout_enabled must be bool
    le = d.get('lockout_enabled')
    if le not in (True, False):
        print('lockout_enabled_invalid')
        sys.exit(1)
    # generated_at must exist and non-empty
    ga = d.get('generated_at')
    if not ga or not str(ga).strip():
        print('generated_at_empty')
        sys.exit(1)
    print('ok')
except Exception as e:
    print('parse:' + str(e))
    sys.exit(2)
" 2>/dev/null || echo "fail")"

if [ "$has_keys" != "ok" ]; then
  FAIL_REASON=risk_state_missing_keys
  {
    echo "MODULE=risk_panel_ui_e2e"
    echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
    echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
    echo "HAS_DAILY_LOSS_BUDGET_PCT=$HAS_DAILY_LOSS_BUDGET_PCT"
    echo "HAS_DAILY_LOSS_BUDGET_USD=$HAS_DAILY_LOSS_BUDGET_USD"
    echo "HAS_TODAY_PNL=$HAS_TODAY_PNL"
    echo "HAS_TODAY_LOSS_PCT=$HAS_TODAY_LOSS_PCT"
    echo "HAS_CONSECUTIVE_LOSSES=$HAS_CONSECUTIVE_LOSSES"
    echo "HAS_NET_EXPOSURE_USD=$HAS_NET_EXPOSURE_USD"
    echo "HAS_POSITIONS_COUNT=$HAS_POSITIONS_COUNT"
    echo "HAS_LOCKOUT_ENABLED=$HAS_LOCKOUT_ENABLED"
    echo "HAS_LOCKOUT_REASON=$HAS_LOCKOUT_REASON"
    echo "HAS_LOCKOUT_UNTIL=$HAS_LOCKOUT_UNTIL"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi

HAS_DAILY_LOSS_BUDGET_PCT=YES
HAS_DAILY_LOSS_BUDGET_USD=YES
HAS_TODAY_PNL=YES
HAS_TODAY_LOSS_PCT=YES
HAS_CONSECUTIVE_LOSSES=YES
HAS_NET_EXPOSURE_USD=YES
HAS_POSITIONS_COUNT=YES
HAS_LOCKOUT_ENABLED=YES
HAS_LOCKOUT_REASON=YES
HAS_LOCKOUT_UNTIL=YES
echo "OK: state has all required keys"

PASS_OR_FAIL=PASS
FAIL_REASON=""
{
  echo "MODULE=risk_panel_ui_e2e"
  echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
  echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
  echo "HAS_DAILY_LOSS_BUDGET_PCT=$HAS_DAILY_LOSS_BUDGET_PCT"
  echo "HAS_DAILY_LOSS_BUDGET_USD=$HAS_DAILY_LOSS_BUDGET_USD"
  echo "HAS_TODAY_PNL=$HAS_TODAY_PNL"
  echo "HAS_TODAY_LOSS_PCT=$HAS_TODAY_LOSS_PCT"
  echo "HAS_CONSECUTIVE_LOSSES=$HAS_CONSECUTIVE_LOSSES"
  echo "HAS_NET_EXPOSURE_USD=$HAS_NET_EXPOSURE_USD"
  echo "HAS_POSITIONS_COUNT=$HAS_POSITIONS_COUNT"
  echo "HAS_LOCKOUT_ENABLED=$HAS_LOCKOUT_ENABLED"
  echo "HAS_LOCKOUT_REASON=$HAS_LOCKOUT_REASON"
  echo "HAS_LOCKOUT_UNTIL=$HAS_LOCKOUT_UNTIL"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
} > "$OUT"
cat "$OUT"
exit 0

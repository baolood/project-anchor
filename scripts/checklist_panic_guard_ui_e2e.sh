#!/usr/bin/env bash
# Panic Guard UI E2E: API-only checks for /ops page controls.
# Step0: GET /ops 200
# Step1: GET /api/proxy/ops/state 200, contains panic state (worker_panic)
# Step2: POST /api/proxy/ops/panic_guard/trigger 200
# Step3: GET state -> worker_panic.triggered=true or last_panic_at set
# Step4: POST /api/proxy/ops/panic_guard/reset 200
# Step5: GET state -> worker_panic.triggered=false or last_panic_at empty
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_panic_guard_ui_e2e_last.out}"
CONSOLE_PRECHECK="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""

echo "=============================="
echo "MODULE=panic_guard_ui_e2e"
echo "Step0: GET /ops 200"
echo "=============================="
ops_code="$(curl -sS --noproxy '*' -o /dev/null -w "%{http_code}" "$CONSOLE_PRECHECK/ops")"
if [ "$ops_code" != "200" ]; then
  echo "FAIL_REASON=ops_page_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: GET /ops 200"

echo "=============================="
echo "Step1: GET /api/proxy/ops/state 200, contains worker_panic"
echo "=============================="
state_resp="$(curl -sS --noproxy '*' -w "\n%{http_code}" "$CONSOLE_PRECHECK/api/proxy/ops/state")"
state_code="$(echo "$state_resp" | tail -1)"
state_body="$(echo "$state_resp" | sed '$d')"
if [ "$state_code" != "200" ]; then
  echo "FAIL_REASON=ops_state_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
has_panic="$(echo "$state_body" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    if 'worker_panic' in d:
        print('yes')
    else:
        print('no')
except:
    print('no')
" 2>/dev/null || echo "no")"
if [ "$has_panic" != "yes" ]; then
  echo "FAIL_REASON=ops_state_missing_worker_panic"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: state contains worker_panic"

echo "=============================="
echo "Step2: POST /api/proxy/ops/panic_guard/trigger 200"
echo "=============================="
post_trigger_resp="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -w "\n%{http_code}" "$CONSOLE_PRECHECK/api/proxy/ops/panic_guard/trigger")"
post_trigger_code="$(echo "$post_trigger_resp" | tail -1)"
if [ "$post_trigger_code" != "200" ]; then
  echo "FAIL_REASON=post_trigger_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: POST trigger 200"
sleep 2

echo "=============================="
echo "Step3: GET /api/proxy/ops/state -> panic triggered"
echo "=============================="
state_resp2="$(curl -sS --noproxy '*' "$CONSOLE_PRECHECK/api/proxy/ops/state")"
triggered="$(echo "$state_resp2" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    wp = d.get('worker_panic')
    if wp is None:
        print('no')
    elif wp.get('triggered') is True:
        print('yes')
    elif wp.get('last_panic_at'):
        print('yes')
    else:
        print('no')
except:
    print('no')
" 2>/dev/null || echo "no")"
if [ "$triggered" != "yes" ]; then
  echo "FAIL_REASON=state_panic_not_triggered"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: panic triggered"

echo "=============================="
echo "Step4: POST /api/proxy/ops/panic_guard/reset 200"
echo "=============================="
post_reset_resp="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -w "\n%{http_code}" "$CONSOLE_PRECHECK/api/proxy/ops/panic_guard/reset")"
post_reset_code="$(echo "$post_reset_resp" | tail -1)"
if [ "$post_reset_code" != "200" ]; then
  echo "FAIL_REASON=post_reset_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: POST reset 200"
sleep 2

echo "=============================="
echo "Step5: GET /api/proxy/ops/state -> panic reset"
echo "=============================="
state_resp3="$(curl -sS --noproxy '*' "$CONSOLE_PRECHECK/api/proxy/ops/state")"
reset_ok="$(echo "$state_resp3" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    wp = d.get('worker_panic')
    if wp is None:
        print('yes')
    elif wp.get('triggered') is False:
        print('yes')
    elif not wp.get('last_panic_at') and (wp.get('count') or 0) == 0:
        print('yes')
    else:
        print('no')
except:
    print('no')
" 2>/dev/null || echo "no")"
if [ "$reset_ok" != "yes" ]; then
  echo "FAIL_REASON=state_panic_not_reset"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  exit 1
fi
echo "OK: panic reset"

PASS_OR_FAIL=PASS
FAIL_REASON=""
echo "=============================="
echo "MODULE=panic_guard_ui_e2e"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"

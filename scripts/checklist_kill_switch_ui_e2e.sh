#!/usr/bin/env bash
# Kill Switch UI E2E: API-only checks for /ops page controls.
# Step0: GET /ops 200
# Step1: GET /api/proxy/ops/state 200, contains kill_switch.enabled
# Step2: POST /api/proxy/ops/kill_switch enabled=true 200
# Step3: GET /api/proxy/ops/state -> kill_switch.enabled=true
# Step4: POST enabled=false 200
# Step5: GET /api/proxy/ops/state -> kill_switch.enabled=false
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_kill_switch_ui_e2e_last.out}"
CONSOLE_PRECHECK="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""

echo "=============================="
echo "MODULE=kill_switch_ui_e2e"
echo "Step0: GET /ops 200"
echo "=============================="
ops_code="$(curl -sS --noproxy '*' -o /dev/null -w "%{http_code}" "$CONSOLE_PRECHECK/ops")"
if [ "$ops_code" != "200" ]; then
  echo "FAIL_REASON=ops_page_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: GET /ops 200"

echo "=============================="
echo "Step1: GET /api/proxy/ops/state 200, contains kill_switch.enabled"
echo "=============================="
state_resp="$(curl -sS --noproxy '*' -w "\n%{http_code}" "$CONSOLE_PRECHECK/api/proxy/ops/state")"
state_code="$(echo "$state_resp" | tail -1)"
state_body="$(echo "$state_resp" | sed '$d')"
if [ "$state_code" != "200" ]; then
  echo "FAIL_REASON=ops_state_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
has_enabled="$(echo "$state_body" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ks = d.get('kill_switch') or {}
    if 'enabled' in ks:
        print('yes')
    else:
        print('no')
except:
    print('no')
" 2>/dev/null || echo "no")"
if [ "$has_enabled" != "yes" ]; then
  echo "FAIL_REASON=ops_state_missing_kill_switch_enabled"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: state contains kill_switch.enabled"

echo "=============================="
echo "Step2: POST /api/proxy/ops/kill_switch enabled=true 200"
echo "=============================="
post_on_resp="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":true}' -w "\n%{http_code}" "$CONSOLE_PRECHECK/api/proxy/ops/kill_switch")"
post_on_code="$(echo "$post_on_resp" | tail -1)"
if [ "$post_on_code" != "200" ]; then
  echo "FAIL_REASON=post_enabled_true_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: POST enabled=true 200"
sleep 2

echo "=============================="
echo "Step3: GET /api/proxy/ops/state -> kill_switch.enabled=true"
echo "=============================="
state_resp2="$(curl -sS --noproxy '*' "$CONSOLE_PRECHECK/api/proxy/ops/state")"
enabled_val="$(echo "$state_resp2" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ks = d.get('kill_switch') or {}
    print(ks.get('enabled', 'missing'))
except:
    print('parse_fail')
" 2>/dev/null || echo "parse_fail")"
if [ "$enabled_val" != "True" ] && [ "$enabled_val" != "true" ]; then
  echo "FAIL_REASON=state_enabled_not_true"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: kill_switch.enabled=true"

echo "=============================="
echo "Step4: POST /api/proxy/ops/kill_switch enabled=false 200"
echo "=============================="
post_off_resp="$(curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":false}' -w "\n%{http_code}" "$CONSOLE_PRECHECK/api/proxy/ops/kill_switch")"
post_off_code="$(echo "$post_off_resp" | tail -1)"
if [ "$post_off_code" != "200" ]; then
  echo "FAIL_REASON=post_enabled_false_not_200"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: POST enabled=false 200"
sleep 2

echo "=============================="
echo "Step5: GET /api/proxy/ops/state -> kill_switch.enabled=false"
echo "=============================="
state_resp3="$(curl -sS --noproxy '*' "$CONSOLE_PRECHECK/api/proxy/ops/state")"
enabled_val2="$(echo "$state_resp3" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ks = d.get('kill_switch') or {}
    v = ks.get('enabled', 'missing')
    print('true' if v is True else 'false' if v is False else str(v))
except:
    print('parse_fail')
" 2>/dev/null || echo "parse_fail")"
if [ "$enabled_val2" != "false" ] && [ "$enabled_val2" != "False" ]; then
  echo "FAIL_REASON=state_enabled_not_false"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: kill_switch.enabled=false"

PASS_OR_FAIL=PASS
FAIL_REASON=""
echo "=============================="
echo "MODULE=kill_switch_ui_e2e"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"

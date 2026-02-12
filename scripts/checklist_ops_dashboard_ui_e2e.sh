#!/usr/bin/env bash
# Ops Dashboard UI E2E: /ops page reachable + proxy /ops/state + /ops/state/history via console.
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_ops_dashboard_ui_e2e_last.out}"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""
PAGE_HTTP_STATUS=""
STATE_HTTP_STATUS=""
HAS_KILL_SWITCH=NO
HAS_WORKER_HEARTBEAT=NO
HAS_PANIC_GUARD=NO
HAS_RECENT_OPS_EVENTS=NO
HAS_HISTORY=NO

echo "=============================="
echo "MODULE=ops_dashboard_ui_e2e"
echo "Step0: GET CONSOLE_URL/ops -> 200"
echo "=============================="
page_code="$(curl -sS -o /dev/null -w "%{http_code}" --noproxy '*' "$CONSOLE_URL/ops" 2>/dev/null || echo "000")"
PAGE_HTTP_STATUS="${page_code}"

if [ "$PAGE_HTTP_STATUS" != "200" ]; then
  FAIL_REASON=ops_page_http_not_200
  {
    echo "MODULE=ops_dashboard_ui_e2e"
    echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
    echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HAS_HISTORY=$HAS_HISTORY"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi
echo "OK: /ops -> 200"

echo "=============================="
echo "Step1: GET CONSOLE_URL/api/proxy/ops/state -> 200 and key checks"
echo "=============================="
state_resp="$(curl -sS --noproxy '*' -w "\n%{http_code}" "$CONSOLE_URL/api/proxy/ops/state")"
STATE_HTTP_STATUS="$(echo "$state_resp" | tail -1)"
state_body="$(echo "$state_resp" | sed '$d')"

if [ "$STATE_HTTP_STATUS" != "200" ]; then
  FAIL_REASON=ops_state_proxy_http_not_200
  {
    echo "MODULE=ops_dashboard_ui_e2e"
    echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
    echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HAS_HISTORY=$HAS_HISTORY"
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
    req = ['kill_switch', 'worker_heartbeat', 'worker_panic', 'recent_ops_events']
    for k in req:
        if k not in d:
            print('missing:' + k)
            sys.exit(1)
    print('ok')
except Exception as e:
    print('parse:' + str(e))
    sys.exit(2)
" 2>/dev/null || echo "fail")"

if [ "$has_keys" != "ok" ]; then
  FAIL_REASON=ops_state_missing_keys
  {
    echo "MODULE=ops_dashboard_ui_e2e"
    echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
    echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HAS_HISTORY=$HAS_HISTORY"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi

HAS_KILL_SWITCH=YES
HAS_WORKER_HEARTBEAT=YES
HAS_PANIC_GUARD=YES
HAS_RECENT_OPS_EVENTS=YES
echo "OK: state has kill_switch, worker_heartbeat, worker_panic, recent_ops_events"

echo "=============================="
echo "Step2: GET CONSOLE_URL/api/proxy/ops/state/history?limit=20 -> 200 and non-empty array"
echo "=============================="
history_resp="$(curl -sS --noproxy '*' -w "\n%{http_code}" "$CONSOLE_URL/api/proxy/ops/state/history?limit=20")"
history_code="$(echo "$history_resp" | tail -1)"
history_body="$(echo "$history_resp" | sed '$d')"

if [ "$history_code" != "200" ]; then
  FAIL_REASON=ops_history_proxy_http_not_200
  {
    echo "MODULE=ops_dashboard_ui_e2e"
    echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
    echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HAS_HISTORY=$HAS_HISTORY"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi

history_len="$(echo "$history_body" | python3 -c "
import json, sys
try:
    arr = json.load(sys.stdin)
    print(len(arr) if isinstance(arr, list) else 0)
except:
    print(0)
" 2>/dev/null || echo "0")"

if [ "${history_len:-0}" -gt 0 ]; then
  HAS_HISTORY=YES
fi

if [ "$HAS_HISTORY" != "YES" ]; then
  FAIL_REASON=ops_history_empty
  {
    echo "MODULE=ops_dashboard_ui_e2e"
    echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
    echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HAS_HISTORY=$HAS_HISTORY"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi

echo "OK: history non-empty (len=$history_len)"

PASS_OR_FAIL=PASS
FAIL_REASON=""
{
  echo "MODULE=ops_dashboard_ui_e2e"
  echo "PAGE_HTTP_STATUS=$PAGE_HTTP_STATUS"
  echo "STATE_HTTP_STATUS=$STATE_HTTP_STATUS"
  echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
  echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
  echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
  echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
  echo "HAS_HISTORY=$HAS_HISTORY"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
} > "$OUT"
cat "$OUT"
exit 0

#!/usr/bin/env bash
# Ops State E2E: GET /ops/state + /ops/state/history, assert fields and history.
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_ops_state_e2e_last.out}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""
HTTP_STATUS=""
HAS_KILL_SWITCH=NO
HAS_WORKER_HEARTBEAT=NO
HAS_PANIC_GUARD=NO
HAS_RECENT_OPS_EVENTS=NO
HISTORY_HTTP_STATUS=""
HISTORY_NON_EMPTY=NO

echo "=============================="
echo "MODULE=ops_state_e2e"
echo "Step0: Precheck backend"
echo "=============================="
if ! curl -sS --noproxy '*' -o /dev/null -w "%{http_code}" "$BACKEND_PRECHECK/health" | grep -q 200; then
  {
    echo "MODULE=ops_state_e2e"
    echo "HTTP_STATUS=0"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HISTORY_HTTP_STATUS=0"
    echo "HISTORY_NON_EMPTY=$HISTORY_NON_EMPTY"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=backend_not_reachable"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi
echo "OK: backend reachable"

echo "=============================="
echo "Step1: GET /ops/state — assert 200 and keys"
echo "=============================="
state_resp="$(curl -sS --noproxy '*' -w "\n%{http_code}" "$BACKEND_PRECHECK/ops/state")"
HTTP_STATUS="$(echo "$state_resp" | tail -1)"
state_body="$(echo "$state_resp" | sed '$d')"

if [ "$HTTP_STATUS" != "200" ]; then
  FAIL_REASON=ops_state_http_not_200
  {
    echo "MODULE=ops_state_e2e"
    echo "HTTP_STATUS=$HTTP_STATUS"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HISTORY_HTTP_STATUS="
    echo "HISTORY_NON_EMPTY=$HISTORY_NON_EMPTY"
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
    echo "MODULE=ops_state_e2e"
    echo "HTTP_STATUS=$HTTP_STATUS"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HISTORY_HTTP_STATUS="
    echo "HISTORY_NON_EMPTY=$HISTORY_NON_EMPTY"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi

# Keys exist; all four required keys present
HAS_KILL_SWITCH=YES
HAS_WORKER_HEARTBEAT=YES
HAS_PANIC_GUARD=YES

echo "=============================="
echo "Step2: POST kill-switch on/off, GET /ops/state — recent_ops_events non-empty"
echo "=============================="
curl_opts=( -sS --noproxy '*' -X POST -H "Content-Type: application/json" )
[ -n "${OPS_TOKEN:-}" ] && curl_opts+=( -H "x-ops-token: $OPS_TOKEN" )
curl "${curl_opts[@]}" -d '{"enabled":true}' "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
sleep 2
curl "${curl_opts[@]}" -d '{"enabled":false}' "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
sleep 2

state_resp2="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/ops/state")"
recent_count="$(echo "$state_resp2" | python3 -c "
import json, sys
d = json.load(sys.stdin)
events = d.get('recent_ops_events') or []
print(len(events))
" 2>/dev/null || echo "0")"

if [ "${recent_count:-0}" -gt 0 ]; then
  HAS_RECENT_OPS_EVENTS=YES
fi
echo "OK: recent_ops_events count=$recent_count"

echo "=============================="
echo "Step3: GET /ops/state/history?limit=20"
echo "=============================="
history_resp="$(curl -sS --noproxy '*' -w "\n%{http_code}" "$BACKEND_PRECHECK/ops/state/history?limit=20")"
HISTORY_HTTP_STATUS="$(echo "$history_resp" | tail -1)"
history_body="$(echo "$history_resp" | sed '$d')"

if [ "$HISTORY_HTTP_STATUS" != "200" ]; then
  FAIL_REASON=ops_state_history_http_not_200
  {
    echo "MODULE=ops_state_e2e"
    echo "HTTP_STATUS=$HTTP_STATUS"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HISTORY_HTTP_STATUS=$HISTORY_HTTP_STATUS"
    echo "HISTORY_NON_EMPTY=$HISTORY_NON_EMPTY"
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
  HISTORY_NON_EMPTY=YES
fi

if [ "$HAS_RECENT_OPS_EVENTS" != "YES" ] || [ "$HISTORY_NON_EMPTY" != "YES" ]; then
  FAIL_REASON=ops_state_events_or_history_empty
  {
    echo "MODULE=ops_state_e2e"
    echo "HTTP_STATUS=$HTTP_STATUS"
    echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
    echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
    echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
    echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
    echo "HISTORY_HTTP_STATUS=$HISTORY_HTTP_STATUS"
    echo "HISTORY_NON_EMPTY=$HISTORY_NON_EMPTY"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } > "$OUT"
  cat "$OUT"
  exit 1
fi

echo "OK: history non-empty (len=$history_len)"

echo "=============================="
echo "Cleanup: kill switch OFF"
echo "=============================="
curl "${curl_opts[@]}" -d '{"enabled":false}' "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
echo "OK: cleanup done"

PASS_OR_FAIL=PASS
FAIL_REASON=""
{
  echo "MODULE=ops_state_e2e"
  echo "HTTP_STATUS=$HTTP_STATUS"
  echo "HAS_KILL_SWITCH=$HAS_KILL_SWITCH"
  echo "HAS_WORKER_HEARTBEAT=$HAS_WORKER_HEARTBEAT"
  echo "HAS_PANIC_GUARD=$HAS_PANIC_GUARD"
  echo "HAS_RECENT_OPS_EVENTS=$HAS_RECENT_OPS_EVENTS"
  echo "HISTORY_HTTP_STATUS=$HISTORY_HTTP_STATUS"
  echo "HISTORY_NON_EMPTY=$HISTORY_NON_EMPTY"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
} > "$OUT"
cat "$OUT"
exit 0

#!/usr/bin/env bash
# Kill Switch Redis E2E: POST /ops/kill-switch sets Redis; worker respects it; events have source=redis.
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_kill_switch_redis_e2e_last.out}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""
OPS_SET_ON_HTTP_STATUS=""
OPS_SET_OFF_HTTP_STATUS=""
NEW_ID=""
STAY_PENDING=NO
EVENTS_HAS_KILL_SWITCH_ON=NO
SOURCE_IS_REDIS=NO

echo "=============================="
echo "MODULE=kill_switch_redis_e2e"
echo "Step0: Precheck backend"
echo "=============================="
if ! curl -sS --noproxy '*' -o /dev/null -w "%{http_code}" "$BACKEND_PRECHECK/health" | grep -q 200; then
  echo "FAIL_REASON=backend_not_reachable"
  echo "OPS_SET_ON_HTTP_STATUS=$OPS_SET_ON_HTTP_STATUS"
  echo "OPS_SET_OFF_HTTP_STATUS=$OPS_SET_OFF_HTTP_STATUS"
  echo "NEW_ID=$NEW_ID"
  echo "STAY_PENDING=$STAY_PENDING"
  echo "EVENTS_HAS_KILL_SWITCH_ON=$EVENTS_HAS_KILL_SWITCH_ON"
  echo "SOURCE_IS_REDIS=$SOURCE_IS_REDIS"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: backend reachable"

echo "=============================="
echo "Step1: POST /ops/kill-switch {\"enabled\": true}"
echo "=============================="
curl_opts=( -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":true}' )
[ -n "${OPS_TOKEN:-}" ] && curl_opts+=( -H "x-ops-token: $OPS_TOKEN" )
ops_on_resp="$(curl "${curl_opts[@]}" -w "\n%{http_code}" "$BACKEND_PRECHECK/ops/kill-switch")"
OPS_SET_ON_HTTP_STATUS="$(echo "$ops_on_resp" | tail -1)"
if [ "$OPS_SET_ON_HTTP_STATUS" != "200" ]; then
  FAIL_REASON=ops_set_on_failed
  echo "OPS_SET_ON_HTTP_STATUS=$OPS_SET_ON_HTTP_STATUS"
  echo "OPS_SET_OFF_HTTP_STATUS=$OPS_SET_OFF_HTTP_STATUS"
  echo "NEW_ID=$NEW_ID"
  echo "STAY_PENDING=$STAY_PENDING"
  echo "EVENTS_HAS_KILL_SWITCH_ON=$EVENTS_HAS_KILL_SWITCH_ON"
  echo "SOURCE_IS_REDIS=$SOURCE_IS_REDIS"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: kill switch ON via Redis"
sleep 2

echo "=============================="
echo "Step2: POST /domain-commands/noop"
echo "=============================="
noop_resp="$(curl -sS --noproxy '*' -X POST "$BACKEND_PRECHECK/domain-commands/noop")"
NEW_ID="$(echo "$noop_resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))")"
if [ -z "$NEW_ID" ]; then
  FAIL_REASON=noop_post_failed
  echo "OPS_SET_ON_HTTP_STATUS=$OPS_SET_ON_HTTP_STATUS"
  echo "OPS_SET_OFF_HTTP_STATUS=$OPS_SET_OFF_HTTP_STATUS"
  echo "NEW_ID=$NEW_ID"
  echo "STAY_PENDING=$STAY_PENDING"
  echo "EVENTS_HAS_KILL_SWITCH_ON=$EVENTS_HAS_KILL_SWITCH_ON"
  echo "SOURCE_IS_REDIS=$SOURCE_IS_REDIS"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "NEW_ID=$NEW_ID"

echo "=============================="
echo "Step3: sleep 12 (pending check 10s), GET status => PENDING"
echo "=============================="
sleep 12
status="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/$NEW_ID" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))")"
if [ "$status" = "PENDING" ]; then
  STAY_PENDING=YES
else
  STAY_PENDING=NO
  FAIL_REASON=command_not_pending
  echo "OPS_SET_ON_HTTP_STATUS=$OPS_SET_ON_HTTP_STATUS"
  echo "OPS_SET_OFF_HTTP_STATUS=$OPS_SET_OFF_HTTP_STATUS"
  echo "NEW_ID=$NEW_ID"
  echo "STAY_PENDING=$STAY_PENDING"
  echo "EVENTS_HAS_KILL_SWITCH_ON=$EVENTS_HAS_KILL_SWITCH_ON"
  echo "SOURCE_IS_REDIS=$SOURCE_IS_REDIS"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  # Turn off kill switch before exit
  curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":false}' "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
  exit 1
fi
echo "OK: command still PENDING"

echo "=============================="
echo "Step4: GET /domain-commands/{id}/events => KILL_SWITCH_ON with source=redis"
echo "=============================="
events="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/$NEW_ID/events")"
has_kill="$(echo "$events" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for e in data:
    if e.get('event_type') == 'KILL_SWITCH_ON':
        print('yes')
        sys.exit(0)
print('no')
" 2>/dev/null || echo "no")"
if [ "$has_kill" = "yes" ]; then
  EVENTS_HAS_KILL_SWITCH_ON=YES
fi
source_redis="$(echo "$events" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for e in data:
    if e.get('event_type') == 'KILL_SWITCH_ON':
        pl = e.get('payload') or {}
        if pl.get('source') == 'redis':
            print('yes')
            sys.exit(0)
print('no')
" 2>/dev/null || echo "no")"
if [ "$source_redis" = "yes" ]; then
  SOURCE_IS_REDIS=YES
fi

if [ "$EVENTS_HAS_KILL_SWITCH_ON" != "YES" ] || [ "$SOURCE_IS_REDIS" != "YES" ]; then
  FAIL_REASON=events_missing_or_wrong_source
  echo "OPS_SET_ON_HTTP_STATUS=$OPS_SET_ON_HTTP_STATUS"
  echo "OPS_SET_OFF_HTTP_STATUS=$OPS_SET_OFF_HTTP_STATUS"
  echo "NEW_ID=$NEW_ID"
  echo "STAY_PENDING=$STAY_PENDING"
  echo "EVENTS_HAS_KILL_SWITCH_ON=$EVENTS_HAS_KILL_SWITCH_ON"
  echo "SOURCE_IS_REDIS=$SOURCE_IS_REDIS"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":false}' "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
  exit 1
fi
echo "OK: KILL_SWITCH_ON with source=redis"

echo "=============================="
echo "Step5: POST /ops/kill-switch {\"enabled\": false}"
echo "=============================="
curl_off_opts=( -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":false}' )
[ -n "${OPS_TOKEN:-}" ] && curl_off_opts+=( -H "x-ops-token: $OPS_TOKEN" )
ops_off_resp="$(curl "${curl_off_opts[@]}" -w "\n%{http_code}" "$BACKEND_PRECHECK/ops/kill-switch")"
OPS_SET_OFF_HTTP_STATUS="$(echo "$ops_off_resp" | tail -1)"
if [ "$OPS_SET_OFF_HTTP_STATUS" != "200" ]; then
  FAIL_REASON=ops_set_off_failed
  echo "OPS_SET_ON_HTTP_STATUS=$OPS_SET_ON_HTTP_STATUS"
  echo "OPS_SET_OFF_HTTP_STATUS=$OPS_SET_OFF_HTTP_STATUS"
  echo "NEW_ID=$NEW_ID"
  echo "STAY_PENDING=$STAY_PENDING"
  echo "EVENTS_HAS_KILL_SWITCH_ON=$EVENTS_HAS_KILL_SWITCH_ON"
  echo "SOURCE_IS_REDIS=$SOURCE_IS_REDIS"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
sleep 3
echo "OK: kill switch OFF"

PASS_OR_FAIL=PASS
FAIL_REASON=""
echo "=============================="
echo "MODULE=kill_switch_redis_e2e"
echo "OPS_SET_ON_HTTP_STATUS=$OPS_SET_ON_HTTP_STATUS"
echo "OPS_SET_OFF_HTTP_STATUS=$OPS_SET_OFF_HTTP_STATUS"
echo "NEW_ID=$NEW_ID"
echo "STAY_PENDING=$STAY_PENDING"
echo "EVENTS_HAS_KILL_SWITCH_ON=$EVENTS_HAS_KILL_SWITCH_ON"
echo "SOURCE_IS_REDIS=$SOURCE_IS_REDIS"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"

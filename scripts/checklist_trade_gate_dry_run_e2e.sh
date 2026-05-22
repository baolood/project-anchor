#!/usr/bin/env bash
# Trade Gate dry-run e2e: submit via Next proxy -> poll command detail -> verify risk FAILED and DONE paths.
set -euo pipefail

CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-}"
FAILED_NOTIONAL="${FAILED_NOTIONAL:-10}"
DONE_NOTIONAL="${DONE_NOTIONAL:-4}"
STOP_PRICE="${STOP_PRICE:-68000}"
LIMIT="${LIMIT:-200}"
CURL_FLAGS=( -sS --connect-timeout 5 --max-time 20 --noproxy '*' )

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

MODULE=trade_gate_dry_run_e2e
FAILED_ID=""
FAILED_STATUS=""
FAILED_ERROR=""
DONE_ID=""
DONE_STATUS=""
DONE_ERROR=""
DONE_EVENTS_HAS_PICKED=NO
DONE_EVENTS_HAS_POLICY_ALLOW=NO
DONE_EVENTS_HAS_ACTION_OK=NO
DONE_EVENTS_HAS_MARK_DONE=NO
PASS_OR_FAIL=FAIL
FAIL_REASON=""

json_get() {
  python3 - "$1" "$2" <<'PY'
import json
import sys

path, key = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(path))
except Exception:
    print("")
    sys.exit(0)
value = data
for part in key.split("."):
    if isinstance(value, dict):
        value = value.get(part, "")
    else:
        value = ""
        break
print("" if value is None else value)
PY
}

write_payload() {
  local path="$1"
  local notional="$2"
  local reason="$3"
  python3 - "$path" "$notional" "$STOP_PRICE" "$reason" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, notional, stop_price, reason = sys.argv[1:5]
payload = {
    "asset": "BTCUSDT",
    "direction": "BUY",
    "hypothetical_notional": notional,
    "stop_price": stop_price,
    "entry_reason": reason,
    "exit_plan": "Exit if BTC breaks invalidation point or assumed loss limit.",
    "emotional_state": "calm",
    "gate_decision": "SIMULATE_ONLY",
    "gate_evaluated_at": datetime.now(timezone.utc).isoformat(),
    "source": "trade_gate_v1",
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(payload, f)
PY
}

submit_trade_gate() {
  local payload="$1"
  local out="$2"
  local code
  code="$(curl "${CURL_FLAGS[@]}" -X POST "$CONSOLE_URL/api/trade-gate/dry-run-intents" \
    -H "Content-Type: application/json" \
    -d "@$payload" \
    -o "$out" -w "%{http_code}")"
  if [ "$code" != "200" ]; then
    echo "SUBMIT_HTTP_$code"
    return 1
  fi
  if [ "$(json_get "$out" status)" != "ok" ]; then
    echo "SUBMIT_STATUS_NOT_OK"
    return 1
  fi
  local id
  id="$(json_get "$out" command_id)"
  if [[ ! "$id" =~ ^order- ]]; then
    echo "SUBMIT_COMMAND_ID_INVALID"
    return 1
  fi
  echo "$id"
}

poll_command() {
  local id="$1"
  local out="$2"
  local status=""
  for _ in $(seq 1 30); do
    curl "${CURL_FLAGS[@]}" "$CONSOLE_URL/api/proxy/commands/$id" -o "$out" || true
    status="$(json_get "$out" status)"
    if [ "$status" = "DONE" ] || [ "$status" = "FAILED" ]; then
      echo "$status"
      return 0
    fi
    sleep 1
  done
  echo "$status"
  return 0
}

events_flags() {
  local id="$1"
  local out="$2"
  local code
  code="$(curl "${CURL_FLAGS[@]}" "$CONSOLE_URL/api/proxy/commands/$id/events?limit=$LIMIT" \
    -o "$out" -w "%{http_code}")"
  if [ "$code" != "200" ]; then
    echo "EVENTS_HTTP_STATUS=$code"
    echo "HAS_PICKED=NO"
    echo "HAS_POLICY_ALLOW=NO"
    echo "HAS_ACTION_OK=NO"
    echo "HAS_MARK_DONE=NO"
    return 0
  fi
  python3 - "$out" <<'PY'
import json
import sys

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    data = []
types = [item.get("event_type") for item in data] if isinstance(data, list) else []
print("EVENTS_HTTP_STATUS=200")
print("HAS_PICKED=" + ("YES" if "PICKED" in types else "NO"))
print("HAS_POLICY_ALLOW=" + ("YES" if "POLICY_ALLOW" in types else "NO"))
print("HAS_ACTION_OK=" + ("YES" if "ACTION_OK" in types else "NO"))
print("HAS_MARK_DONE=" + ("YES" if "MARK_DONE" in types else "NO"))
PY
}

echo "== Step0 Precheck =="
home_body="$tmpdir/home.html"
home_code="$(curl "${CURL_FLAGS[@]}" "$CONSOLE_URL/trade-gate" -o "$home_body" -w "%{http_code}" || true)"
if [ "$home_code" != "200" ]; then
  FAIL_REASON="CONSOLE_TRADE_GATE_NOT_READY_HTTP_$home_code"
  echo "MODULE=$MODULE"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
if [ -n "$BACKEND_PRECHECK" ]; then
  backend_code="$(curl "${CURL_FLAGS[@]}" "$BACKEND_PRECHECK/health" -o "$tmpdir/backend_health.json" -w "%{http_code}" || true)"
  if [ "$backend_code" != "200" ]; then
    FAIL_REASON="BACKEND_PRECHECK_HTTP_$backend_code"
    echo "MODULE=$MODULE"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
    exit 1
  fi
fi
echo "OK: precheck passed"

echo "== Step1 Submit risk-failed dry-run intent (notional=$FAILED_NOTIONAL) =="
failed_payload="$tmpdir/failed_payload.json"
failed_submit="$tmpdir/failed_submit.json"
failed_detail="$tmpdir/failed_detail.json"
write_payload "$failed_payload" "$FAILED_NOTIONAL" "Dry-run risk-failed path smoke."
FAILED_ID="$(submit_trade_gate "$failed_payload" "$failed_submit")" || {
  FAIL_REASON="$FAILED_ID"
  echo "MODULE=$MODULE"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
}
FAILED_STATUS="$(poll_command "$FAILED_ID" "$failed_detail")"
FAILED_ERROR="$(json_get "$failed_detail" error)"
if [ "$FAILED_STATUS" != "FAILED" ] || ! echo "$FAILED_ERROR" | grep -q "RISK_HARD_LIMITS"; then
  FAIL_REASON="RISK_FAILED_PATH_NOT_BLOCKED"
  echo "MODULE=$MODULE"
  echo "FAILED_ID=$FAILED_ID"
  echo "FAILED_STATUS=$FAILED_STATUS"
  echo "FAILED_ERROR=$FAILED_ERROR"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: risk-failed path blocked by hard limits"

echo "== Step2 Submit DONE dry-run intent (notional=$DONE_NOTIONAL) =="
done_payload="$tmpdir/done_payload.json"
done_submit="$tmpdir/done_submit.json"
done_detail="$tmpdir/done_detail.json"
done_events="$tmpdir/done_events.json"
done_events_flags="$tmpdir/done_events_flags.txt"
write_payload "$done_payload" "$DONE_NOTIONAL" "Dry-run DONE path smoke."
DONE_ID="$(submit_trade_gate "$done_payload" "$done_submit")" || {
  FAIL_REASON="$DONE_ID"
  echo "MODULE=$MODULE"
  echo "FAILED_ID=$FAILED_ID"
  echo "FAILED_STATUS=$FAILED_STATUS"
  echo "FAILED_ERROR=$FAILED_ERROR"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
}
DONE_STATUS="$(poll_command "$DONE_ID" "$done_detail")"
DONE_ERROR="$(json_get "$done_detail" error)"
if [ "$DONE_STATUS" != "DONE" ]; then
  FAIL_REASON="DONE_PATH_NOT_DONE"
  echo "MODULE=$MODULE"
  echo "FAILED_ID=$FAILED_ID"
  echo "FAILED_STATUS=$FAILED_STATUS"
  echo "FAILED_ERROR=$FAILED_ERROR"
  echo "DONE_ID=$DONE_ID"
  echo "DONE_STATUS=$DONE_STATUS"
  echo "DONE_ERROR=$DONE_ERROR"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi

events_flags "$DONE_ID" "$done_events" > "$done_events_flags"
DONE_EVENTS_HAS_PICKED="$(grep HAS_PICKED= "$done_events_flags" | cut -d= -f2)"
DONE_EVENTS_HAS_POLICY_ALLOW="$(grep HAS_POLICY_ALLOW= "$done_events_flags" | cut -d= -f2)"
DONE_EVENTS_HAS_ACTION_OK="$(grep HAS_ACTION_OK= "$done_events_flags" | cut -d= -f2)"
DONE_EVENTS_HAS_MARK_DONE="$(grep HAS_MARK_DONE= "$done_events_flags" | cut -d= -f2)"
if [ "$DONE_EVENTS_HAS_PICKED" != "YES" ] ||
   [ "$DONE_EVENTS_HAS_POLICY_ALLOW" != "YES" ] ||
   [ "$DONE_EVENTS_HAS_ACTION_OK" != "YES" ] ||
   [ "$DONE_EVENTS_HAS_MARK_DONE" != "YES" ]; then
  FAIL_REASON="DONE_EVENTS_MISSING"
  echo "MODULE=$MODULE"
  echo "FAILED_ID=$FAILED_ID"
  echo "FAILED_STATUS=$FAILED_STATUS"
  echo "FAILED_ERROR=$FAILED_ERROR"
  echo "DONE_ID=$DONE_ID"
  echo "DONE_STATUS=$DONE_STATUS"
  echo "DONE_ERROR=$DONE_ERROR"
  echo "DONE_EVENTS_HAS_PICKED=$DONE_EVENTS_HAS_PICKED"
  echo "DONE_EVENTS_HAS_POLICY_ALLOW=$DONE_EVENTS_HAS_POLICY_ALLOW"
  echo "DONE_EVENTS_HAS_ACTION_OK=$DONE_EVENTS_HAS_ACTION_OK"
  echo "DONE_EVENTS_HAS_MARK_DONE=$DONE_EVENTS_HAS_MARK_DONE"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  exit 1
fi
echo "OK: DONE path completed with expected events"

PASS_OR_FAIL=PASS
FAIL_REASON=""
echo "=============================="
echo "MODULE=$MODULE"
echo "CONSOLE_URL=$CONSOLE_URL"
echo "BACKEND_PRECHECK=$BACKEND_PRECHECK"
echo "FAILED_ID=$FAILED_ID"
echo "FAILED_STATUS=$FAILED_STATUS"
echo "FAILED_ERROR=$FAILED_ERROR"
echo "DONE_ID=$DONE_ID"
echo "DONE_STATUS=$DONE_STATUS"
echo "DONE_ERROR=$DONE_ERROR"
echo "DONE_EVENTS_HAS_PICKED=$DONE_EVENTS_HAS_PICKED"
echo "DONE_EVENTS_HAS_POLICY_ALLOW=$DONE_EVENTS_HAS_POLICY_ALLOW"
echo "DONE_EVENTS_HAS_ACTION_OK=$DONE_EVENTS_HAS_ACTION_OK"
echo "DONE_EVENTS_HAS_MARK_DONE=$DONE_EVENTS_HAS_MARK_DONE"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
exit 0

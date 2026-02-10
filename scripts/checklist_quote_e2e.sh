#!/usr/bin/env bash
# QUOTE e2e: create via proxy -> poll DONE -> check result + events. Optional: policy block when POLICY_QUOTE_MAX_NOTIONAL>0.
set -euo pipefail

CONSOLE_PRECHECK="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

MODULE=command_quote_end_to_end
NEW_ID=""
FINAL_STATUS=""
RESULT_OK=NO
EVENTS_HAS_PICKED=NO
EVENTS_HAS_ACTION_OK=NO
EVENTS_HAS_MARK_DONE=NO
PASS_OR_FAIL=FAIL
FAIL_REASON=""

echo "Step0: Precheck (console + backend)"
echo "Step0: CONSOLE_PRECHECK=$CONSOLE_PRECHECK BACKEND_PRECHECK=$BACKEND_PRECHECK"
lsof -nP -iTCP:3000 -sTCP:LISTEN || true
lsof -nP -iTCP:8000 -sTCP:LISTEN || true

# Optional: policy block test (notional=100, max=50 -> FAILED + POLICY_BLOCK)
if [ -n "${POLICY_QUOTE_MAX_NOTIONAL:-}" ] && [ "${POLICY_QUOTE_MAX_NOTIONAL:-0}" -gt 0 ]; then
  echo "Step0b: Policy block test (POLICY_QUOTE_MAX_NOTIONAL=$POLICY_QUOTE_MAX_NOTIONAL)"
  block_body="$tmpdir/quote_block.json"
  curl -sS --noproxy '*' -X POST "$CONSOLE_PRECHECK/api/proxy/commands/quote" \
    -H "Content-Type: application/json" \
    -d '{"notional":100}' \
    -o "$block_body"
  block_id="$(python3 - "$block_body" <<'PY'
import json,sys
print(json.load(open(sys.argv[1])).get("id",""))
PY
)"
  for i in $(seq 1 30); do
    st="$(curl -sS --noproxy '*' "$CONSOLE_PRECHECK/api/proxy/commands/$block_id" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))")"
    [ "$st" = "FAILED" ] && break
    [ "$st" = "DONE" ] && { echo "FAIL: expected FAILED when notional>max"; exit 1; }
    sleep 1
  done
  ev="$(curl -sS --noproxy '*' "$CONSOLE_PRECHECK/api/proxy/commands/$block_id/events?limit=200")"
  if echo "$ev" | python3 -c "import json,sys; d=json.load(sys.stdin); types=[e.get('event_type') for e in d] if isinstance(d,list) else []; sys.exit(0 if 'POLICY_BLOCK' in types else 1)" 2>/dev/null; then
    echo "OK: policy block test passed (POLICY_BLOCK present)"
  else
    echo "FAIL: POLICY_BLOCK not found in events"
    exit 1
  fi
  echo "MODULE=$MODULE"
  echo "NEW_ID=$block_id"
  echo "FINAL_STATUS=FAILED"
  echo "RESULT_OK=NO"
  echo "EVENTS_HAS_PICKED=YES"
  echo "EVENTS_HAS_ACTION_OK=NO"
  echo "EVENTS_HAS_MARK_DONE=NO"
  echo "PASS_OR_FAIL=PASS"
  echo "FAIL_REASON="
  exit 0
fi

echo "Step1: POST /api/proxy/commands/quote -> 200, type==QUOTE, status==PENDING, id prefix quote-"
create_body="$tmpdir/quote_create.json"
create_http="$(curl -sS --noproxy '*' -X POST "$CONSOLE_PRECHECK/api/proxy/commands/quote" \
  -H "Content-Type: application/json" \
  -d '{}' \
  -o "$create_body" -w "%{http_code}")"
python3 - "$create_body" "$create_http" <<'PY'
import json, sys
body_path, status = sys.argv[1], sys.argv[2]
if status != "200":
    print("FAIL_REASON=QUOTE_CREATE_HTTP_" + status)
    sys.exit(1)
obj = json.load(open(body_path))
if obj.get("type") != "QUOTE":
    print("FAIL_REASON=QUOTE_CREATE_TYPE_MISMATCH")
    sys.exit(1)
if obj.get("status") != "PENDING":
    print("FAIL_REASON=QUOTE_CREATE_STATUS_NOT_PENDING")
    sys.exit(1)
if not str(obj.get("id","")).startswith("quote-"):
    print("FAIL_REASON=QUOTE_CREATE_ID_PREFIX")
    sys.exit(1)
print("OK: quote created")
PY
NEW_ID="$(python3 -c "import json; print(json.load(open('$create_body'))['id'])")"
echo "NEW_ID=$NEW_ID"

echo "Step2: Poll GET /api/proxy/commands/{id} until DONE (max 30 x 1s)"
last_detail="$tmpdir/detail_last.json"
for i in $(seq 1 30); do
  curl -sS --noproxy '*' "$CONSOLE_PRECHECK/api/proxy/commands/$NEW_ID" -o "$last_detail"
  FINAL_STATUS="$(python3 -c "import json; print(json.load(open('$last_detail')).get('status',''))")"
  [ "$FINAL_STATUS" = "DONE" ] && break
  [ "$FINAL_STATUS" = "FAILED" ] && { FAIL_REASON="QUOTE_FAILED"; break; }
  sleep 1
done
echo "FINAL_STATUS=$FINAL_STATUS"

if [ "$FINAL_STATUS" != "DONE" ]; then
  echo "MODULE=$MODULE"
  echo "NEW_ID=$NEW_ID"
  echo "FINAL_STATUS=$FINAL_STATUS"
  echo "RESULT_OK=NO"
  echo "EVENTS_HAS_PICKED=NO"
  echo "EVENTS_HAS_ACTION_OK=NO"
  echo "EVENTS_HAS_MARK_DONE=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=${FAIL_REASON:-TIMEOUT_OR_FAILED}"
  exit 1
fi

echo "Step3: Check result.type==quote, price>0, qty>0"
result_json="$(python3 -c "import json; d=json.load(open('$last_detail')); print(json.dumps(d.get('result') or {}))")"
python3 - "$result_json" <<'PY'
import json, sys
r = json.loads(sys.argv[1]) if sys.argv[1] else {}
if r.get("type") != "quote":
    print("FAIL_REASON=RESULT_TYPE_NOT_QUOTE")
    sys.exit(1)
if not (isinstance(r.get("price"), (int, float)) and r.get("price", 0) > 0):
    print("FAIL_REASON=RESULT_PRICE_INVALID")
    sys.exit(1)
if not (isinstance(r.get("qty"), (int, float)) and r.get("qty", 0) > 0):
    print("FAIL_REASON=RESULT_QTY_INVALID")
    sys.exit(1)
print("OK: result valid")
PY
RESULT_OK=YES

echo "Step4: GET /api/proxy/commands/{id}/events?limit=200 -> 200, contains PICKED, ACTION_OK, MARK_DONE"
ev_body="$tmpdir/events.json"
ev_code="$(curl -sS --noproxy '*' -o "$ev_body" -w "%{http_code}" "$CONSOLE_PRECHECK/api/proxy/commands/$NEW_ID/events?limit=200")"
[ "$ev_code" != "200" ] && { FAIL_REASON="EVENTS_HTTP_$ev_code"; }
python3 - "$ev_body" <<'PY' > "$tmpdir/events.out"
import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except Exception:
    print("EVENTS_HAS_PICKED=NO")
    print("EVENTS_HAS_ACTION_OK=NO")
    print("EVENTS_HAS_MARK_DONE=NO")
    sys.exit(0)
types = [e.get("event_type") for e in data] if isinstance(data, list) else []
print("EVENTS_HAS_PICKED=" + ("YES" if "PICKED" in types else "NO"))
print("EVENTS_HAS_ACTION_OK=" + ("YES" if "ACTION_OK" in types else "NO"))
print("EVENTS_HAS_MARK_DONE=" + ("YES" if "MARK_DONE" in types else "NO"))
PY
EVENTS_HAS_PICKED="$(grep EVENTS_HAS_PICKED= "$tmpdir/events.out" | cut -d= -f2)"
EVENTS_HAS_ACTION_OK="$(grep EVENTS_HAS_ACTION_OK= "$tmpdir/events.out" | cut -d= -f2)"
EVENTS_HAS_MARK_DONE="$(grep EVENTS_HAS_MARK_DONE= "$tmpdir/events.out" | cut -d= -f2)"

[ "$EVENTS_HAS_PICKED" = "YES" ] && [ "$EVENTS_HAS_ACTION_OK" = "YES" ] && [ "$EVENTS_HAS_MARK_DONE" = "YES" ] && PASS_OR_FAIL=PASS || { [ -z "$FAIL_REASON" ] && FAIL_REASON="EVENTS_MISSING"; }

echo "MODULE=$MODULE"
echo "NEW_ID=$NEW_ID"
echo "FINAL_STATUS=$FINAL_STATUS"
echo "RESULT_OK=$RESULT_OK"
echo "EVENTS_HAS_PICKED=$EVENTS_HAS_PICKED"
echo "EVENTS_HAS_ACTION_OK=$EVENTS_HAS_ACTION_OK"
echo "EVENTS_HAS_MARK_DONE=$EVENTS_HAS_MARK_DONE"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
[ "$PASS_OR_FAIL" = "PASS" ] || exit 1
exit 0

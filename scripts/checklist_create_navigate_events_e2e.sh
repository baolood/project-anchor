#!/usr/bin/env bash
# Create quote -> poll DONE -> GET events 200 with PICKED + ACTION_OK + MARK_DONE (simulates create→detail→autoevents flow).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

MODULE=create_navigate_events_e2e
QUOTE_ID=""
EVENTS_HTTP_STATUS=""
HAS_PICKED=NO
HAS_ACTION_OK=NO
HAS_MARK_DONE=NO
PASS_OR_FAIL=FAIL
FAIL_REASON=""

parse_http() {
  python3 - "$1" <<'PY'
import sys
path = sys.argv[1]
raw = open(path, "rb").read().decode("utf-8", errors="replace")
raw = raw.replace("\r\n", "\n").replace("\r", "\n")
lines = raw.split("\n")
if not lines:
    print("0")
    print("")
    sys.exit(0)
parts = lines[0].strip().split()
status_code = parts[1] if len(parts) >= 2 else "0"
body_lines = []
found_blank = False
for i in range(1, len(lines)):
    if lines[i].strip() == "":
        found_blank = True
        continue
    if found_blank:
        body_lines.append(lines[i])
print(status_code)
print("\n".join(body_lines))
PY
}

echo "== Step0 Precheck =="
get_home="$tmpdir/get_home.txt"
curl -sS -i --noproxy '*' "$CONSOLE_URL/" -o "$get_home" || true
home_status="$(parse_http "$get_home" | head -1)"
if [ "$home_status" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "QUOTE_ID="
  echo "EVENTS_HTTP_STATUS="
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_OK=NO"
  echo "HAS_MARK_DONE=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=CONSOLE_NOT_READY"
  exit 1
fi

echo "== Step1 Create QUOTE (with payload) =="
quote_resp="$tmpdir/quote_resp.txt"
curl -sS -i --noproxy '*' -X POST "$CONSOLE_URL/api/proxy/commands/quote" \
  -H "content-type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","notional":100}' \
  -o "$quote_resp" || true
quote_status="$(parse_http "$quote_resp" | head -1)"
quote_body="$tmpdir/quote_body.json"
parse_http "$quote_resp" | sed -n '2,$p' > "$quote_body"
if [ "$quote_status" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "QUOTE_ID="
  echo "EVENTS_HTTP_STATUS="
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_OK=NO"
  echo "HAS_MARK_DONE=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=QUOTE_CREATE_HTTP_${quote_status}"
  exit 1
fi
QUOTE_ID="$(python3 - "$quote_body" <<'PY'
import json, sys
path = sys.argv[1]
d = json.load(open(path))
i = d.get("id", "")
if not str(i).startswith("quote-"):
    sys.exit(2)
print(i)
PY
)" || { echo "FAIL_REASON=QUOTE_ID_PREFIX"; exit 1; }
echo "QUOTE_ID=$QUOTE_ID"

echo "== Step2 Poll QUOTE until DONE (max 30 x 1s) =="
detail_file="$tmpdir/detail.json"
for _ in $(seq 1 30); do
  curl -sS --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$QUOTE_ID" -o "$detail_file" || true
  st="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
  [ "$st" = "DONE" ] && break
  sleep 1
done
st="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
if [ "$st" != "DONE" ]; then
  echo "MODULE=$MODULE"
  echo "QUOTE_ID=$QUOTE_ID"
  echo "EVENTS_HTTP_STATUS="
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_OK=NO"
  echo "HAS_MARK_DONE=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=QUOTE_NOT_DONE"
  exit 1
fi

echo "== Step3 GET events =="
events_resp="$tmpdir/events_resp.txt"
curl -sS -i --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$QUOTE_ID/events?limit=200" -o "$events_resp" || true
EVENTS_HTTP_STATUS="$(parse_http "$events_resp" | head -1)"
events_body="$tmpdir/events_body.json"
parse_http "$events_resp" | sed -n '2,$p' > "$events_body"
if [ "$EVENTS_HTTP_STATUS" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "QUOTE_ID=$QUOTE_ID"
  echo "EVENTS_HTTP_STATUS=$EVENTS_HTTP_STATUS"
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_OK=NO"
  echo "HAS_MARK_DONE=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=EVENTS_HTTP_${EVENTS_HTTP_STATUS}"
  exit 1
fi
python3 - "$events_body" <<'PY' > "$tmpdir/events_flags.txt" || true
import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except Exception:
    print("HAS_PICKED=NO")
    print("HAS_ACTION_OK=NO")
    print("HAS_MARK_DONE=NO")
    sys.exit(0)
types = [e.get("event_type") for e in data] if isinstance(data, list) else []
print("HAS_PICKED=" + ("YES" if "PICKED" in types else "NO"))
print("HAS_ACTION_OK=" + ("YES" if "ACTION_OK" in types else "NO"))
print("HAS_MARK_DONE=" + ("YES" if "MARK_DONE" in types else "NO"))
PY
HAS_PICKED="$(grep HAS_PICKED= "$tmpdir/events_flags.txt" | cut -d= -f2)"
HAS_ACTION_OK="$(grep HAS_ACTION_OK= "$tmpdir/events_flags.txt" | cut -d= -f2)"
HAS_MARK_DONE="$(grep HAS_MARK_DONE= "$tmpdir/events_flags.txt" | cut -d= -f2)"

if [ "$HAS_PICKED" = "YES" ] && [ "$HAS_ACTION_OK" = "YES" ] && [ "$HAS_MARK_DONE" = "YES" ]; then
  PASS_OR_FAIL=PASS
  FAIL_REASON=""
else
  PASS_OR_FAIL=FAIL
  [ -z "$FAIL_REASON" ] && FAIL_REASON=EVENTS_MISSING_TYPES
fi

echo "=============================="
echo "MODULE=$MODULE"
echo "QUOTE_ID=$QUOTE_ID"
echo "EVENTS_HTTP_STATUS=$EVENTS_HTTP_STATUS"
echo "HAS_PICKED=$HAS_PICKED"
echo "HAS_ACTION_OK=$HAS_ACTION_OK"
echo "HAS_MARK_DONE=$HAS_MARK_DONE"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
[ "$PASS_OR_FAIL" = "PASS" ] || exit 1
exit 0

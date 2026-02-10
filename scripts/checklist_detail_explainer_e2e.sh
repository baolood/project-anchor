#!/usr/bin/env bash
# Create FAIL -> poll FAILED -> GET events -> assert ACTION_FAIL/MARK_FAILED/PICKED and expected reason title.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"
LIMIT="${LIMIT:-200}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

MODULE=detail_explainer_e2e
FAIL_ID=""
EVENTS_HTTP_STATUS=""
HAS_PICKED=NO
HAS_ACTION_FAIL=NO
HAS_MARK_FAILED=NO
EXPECTED_TITLE=""
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
  echo "FAIL_ID="
  echo "EVENTS_HTTP_STATUS="
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_FAIL=NO"
  echo "HAS_MARK_FAILED=NO"
  echo "EXPECTED_TITLE="
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=CONSOLE_NOT_READY"
  exit 1
fi

echo "== Step1 POST fail =="
fail_resp="$tmpdir/fail_resp.txt"
curl -sS -i --noproxy '*' -X POST "$CONSOLE_URL/api/proxy/commands/fail" -o "$fail_resp" || true
fail_status="$(parse_http "$fail_resp" | head -1)"
fail_body="$tmpdir/fail_body.json"
parse_http "$fail_resp" | sed -n '2,$p' > "$fail_body"
if [ "$fail_status" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "FAIL_ID="
  echo "EVENTS_HTTP_STATUS="
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_FAIL=NO"
  echo "HAS_MARK_FAILED=NO"
  echo "EXPECTED_TITLE="
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=FAIL_CREATE_HTTP_${fail_status}"
  exit 1
fi
FAIL_ID="$(python3 - "$fail_body" <<'PY'
import json, sys
path = sys.argv[1]
d = json.load(open(path))
i = d.get("id", "")
if not str(i).startswith("fail-"):
    sys.exit(2)
print(i)
PY
)" || { echo "FAIL_REASON=FAIL_ID_PREFIX"; exit 1; }
echo "FAIL_ID=$FAIL_ID"

echo "== Step2 Poll until FAILED (max 30 x 1s) =="
detail_file="$tmpdir/detail.json"
for _ in $(seq 1 30); do
  curl -sS --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$FAIL_ID" -o "$detail_file" || true
  st="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
  [ "$st" = "FAILED" ] && break
  sleep 1
done
st="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
if [ "$st" != "FAILED" ]; then
  echo "MODULE=$MODULE"
  echo "FAIL_ID=$FAIL_ID"
  echo "EVENTS_HTTP_STATUS="
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_FAIL=NO"
  echo "HAS_MARK_FAILED=NO"
  echo "EXPECTED_TITLE="
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=DID_NOT_REACH_FAILED"
  exit 1
fi

echo "== Step3 GET events =="
events_resp="$tmpdir/events_resp.txt"
curl -sS -i --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$FAIL_ID/events?limit=$LIMIT" -o "$events_resp" || true
EVENTS_HTTP_STATUS="$(parse_http "$events_resp" | head -1)"
events_body="$tmpdir/events_body.json"
parse_http "$events_resp" | sed -n '2,$p' > "$events_body"
if [ "$EVENTS_HTTP_STATUS" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "FAIL_ID=$FAIL_ID"
  echo "EVENTS_HTTP_STATUS=$EVENTS_HTTP_STATUS"
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_FAIL=NO"
  echo "HAS_MARK_FAILED=NO"
  echo "EXPECTED_TITLE="
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=EVENTS_HTTP_${EVENTS_HTTP_STATUS}"
  exit 1
fi

echo "== Step4 Assert event types + compute expected title =="
python3 - "$events_body" <<'PY' > "$tmpdir/explainer_out.txt" || true
import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except Exception:
    print("HAS_PICKED=NO")
    print("HAS_ACTION_FAIL=NO")
    print("HAS_MARK_FAILED=NO")
    print("EXPECTED_TITLE=")
    sys.exit(1)
types = [e.get("event_type") for e in data] if isinstance(data, list) else []
has_picked = "PICKED" in types
has_action_fail = "ACTION_FAIL" in types
has_mark_failed = "MARK_FAILED" in types
# Priority: POLICY_BLOCK > ACTION_FAIL > EXCEPTION
if "POLICY_BLOCK" in types:
    expected = "Blocked by policy"
elif "ACTION_FAIL" in types:
    expected = "Action failed"
elif "EXCEPTION" in types:
    expected = "Exception"
else:
    expected = "Processing"
print("HAS_PICKED=" + ("YES" if has_picked else "NO"))
print("HAS_ACTION_FAIL=" + ("YES" if has_action_fail else "NO"))
print("HAS_MARK_FAILED=" + ("YES" if has_mark_failed else "NO"))
print("EXPECTED_TITLE=" + expected)
PY
HAS_PICKED="$(grep HAS_PICKED= "$tmpdir/explainer_out.txt" | cut -d= -f2)"
HAS_ACTION_FAIL="$(grep HAS_ACTION_FAIL= "$tmpdir/explainer_out.txt" | cut -d= -f2)"
HAS_MARK_FAILED="$(grep HAS_MARK_FAILED= "$tmpdir/explainer_out.txt" | cut -d= -f2)"
EXPECTED_TITLE="$(grep EXPECTED_TITLE= "$tmpdir/explainer_out.txt" | cut -d= -f2-)"

if [ "$HAS_PICKED" = "YES" ] && [ "$HAS_ACTION_FAIL" = "YES" ] && [ "$HAS_MARK_FAILED" = "YES" ]; then
  PASS_OR_FAIL=PASS
  FAIL_REASON=""
else
  PASS_OR_FAIL=FAIL
  [ -z "$FAIL_REASON" ] && FAIL_REASON=MISSING_EVENT_TYPES
fi

echo "=============================="
echo "MODULE=$MODULE"
echo "FAIL_ID=$FAIL_ID"
echo "EVENTS_HTTP_STATUS=$EVENTS_HTTP_STATUS"
echo "HAS_PICKED=$HAS_PICKED"
echo "HAS_ACTION_FAIL=$HAS_ACTION_FAIL"
echo "HAS_MARK_FAILED=$HAS_MARK_FAILED"
echo "EXPECTED_TITLE=$EXPECTED_TITLE"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
[ "$PASS_OR_FAIL" = "PASS" ] || exit 1
exit 0

#!/usr/bin/env bash
# Create-form UI e2e: POST quote with payload -> poll DONE -> result.type=quote; POST fail no payload -> poll FAILED.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

MODULE=console_create_form_ui_e2e
QUOTE_ID=""
QUOTE_FINAL_STATUS=""
QUOTE_RESULT_TYPE_OK=NO
FAIL_ID=""
FAIL_FINAL_STATUS=""
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
  echo "QUOTE_FINAL_STATUS="
  echo "QUOTE_RESULT_TYPE_OK=NO"
  echo "FAIL_ID="
  echo "FAIL_FINAL_STATUS="
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
  echo "QUOTE_FINAL_STATUS="
  echo "QUOTE_RESULT_TYPE_OK=NO"
  echo "FAIL_ID="
  echo "FAIL_FINAL_STATUS="
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
  [ "$st" = "FAILED" ] && QUOTE_FINAL_STATUS=FAILED && break
  sleep 1
done
QUOTE_FINAL_STATUS="${QUOTE_FINAL_STATUS:-$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")}"

result_type="$(python3 - "$detail_file" <<'PY'
import json, sys
path = sys.argv[1]
try:
    d = json.load(open(path))
    r = d.get("result") or {}
    print(r.get("type", ""))
except Exception:
    print("")
PY
)" || true
[ "$result_type" = "quote" ] && QUOTE_RESULT_TYPE_OK=YES || QUOTE_RESULT_TYPE_OK=NO

echo "== Step3 Create FAIL (no payload) =="
fail_resp="$tmpdir/fail_resp.txt"
curl -sS -i --noproxy '*' -X POST "$CONSOLE_URL/api/proxy/commands/fail" -o "$fail_resp" || true
fail_status="$(parse_http "$fail_resp" | head -1)"
fail_body="$tmpdir/fail_body.json"
parse_http "$fail_resp" | sed -n '2,$p' > "$fail_body"
if [ "$fail_status" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "QUOTE_ID=$QUOTE_ID"
  echo "QUOTE_FINAL_STATUS=$QUOTE_FINAL_STATUS"
  echo "QUOTE_RESULT_TYPE_OK=$QUOTE_RESULT_TYPE_OK"
  echo "FAIL_ID="
  echo "FAIL_FINAL_STATUS="
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

echo "== Step4 Poll FAIL until FAILED (max 30 x 1s) =="
for _ in $(seq 1 30); do
  curl -sS --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$FAIL_ID" -o "$detail_file" || true
  st="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
  [ "$st" = "FAILED" ] && FAIL_FINAL_STATUS=FAILED && break
  sleep 1
done
FAIL_FINAL_STATUS="${FAIL_FINAL_STATUS:-$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")}"

if [ "$QUOTE_FINAL_STATUS" = "DONE" ] && [ "$QUOTE_RESULT_TYPE_OK" = "YES" ] && [ "$FAIL_FINAL_STATUS" = "FAILED" ]; then
  PASS_OR_FAIL=PASS
  FAIL_REASON=""
else
  PASS_OR_FAIL=FAIL
  [ -z "$FAIL_REASON" ] && FAIL_REASON=CHECK_FAILED
fi

echo "=============================="
echo "MODULE=$MODULE"
echo "QUOTE_ID=$QUOTE_ID"
echo "QUOTE_FINAL_STATUS=$QUOTE_FINAL_STATUS"
echo "QUOTE_RESULT_TYPE_OK=$QUOTE_RESULT_TYPE_OK"
echo "FAIL_ID=$FAIL_ID"
echo "FAIL_FINAL_STATUS=$FAIL_FINAL_STATUS"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
[ "$PASS_OR_FAIL" = "PASS" ] || exit 1
exit 0

#!/usr/bin/env bash
# Create payload schema UI e2e: code check for QUOTE validation (symbol, side BUY/SELL, notional > 0)
# + runtime: POST quote with valid payload -> poll DONE -> assert result.type == "quote".
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONSOLE_DIR="${CONSOLE_DIR:-$ROOT/anchor-console}"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"
LIMIT="${LIMIT:-200}"
OUT="${OUT:-/tmp/anchor_e2e_checklist_create_payload_schema_ui_e2e_last.out}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

MODULE=create_payload_schema_ui_e2e
CODE_HAS_QUOTE_VALIDATION=NO
QUOTE_ID=""
QUOTE_FINAL_STATUS=""
QUOTE_RESULT_TYPE_OK=NO
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

echo "== Step0 Code check: QUOTE validation in app/page.tsx =="
page_file="$CONSOLE_DIR/app/page.tsx"
if [ ! -f "$page_file" ]; then
  CODE_HAS_QUOTE_VALIDATION=NO
  FAIL_REASON=CODE_PAGE_MISSING
else
  if grep -q "Symbol is required" "$page_file" 2>/dev/null && \
     grep -q "Notional must be" "$page_file" 2>/dev/null && \
     grep -qE "BUY|SELL" "$page_file" 2>/dev/null; then
    CODE_HAS_QUOTE_VALIDATION=YES
  else
    CODE_HAS_QUOTE_VALIDATION=NO
    [ -z "$FAIL_REASON" ] && FAIL_REASON=CODE_MISSING_QUOTE_VALIDATION
  fi
fi
echo "CODE_HAS_QUOTE_VALIDATION=$CODE_HAS_QUOTE_VALIDATION"

echo "== Step1 Precheck CONSOLE_URL =="
get_home="$tmpdir/get_home.txt"
curl -sS -i --noproxy '*' "$CONSOLE_URL/" -o "$get_home" || true
home_status="$(parse_http "$get_home" | head -1)"
if [ "$home_status" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "CODE_HAS_QUOTE_VALIDATION=$CODE_HAS_QUOTE_VALIDATION"
  echo "QUOTE_ID="
  echo "QUOTE_FINAL_STATUS="
  echo "QUOTE_RESULT_TYPE_OK=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=CONSOLE_NOT_READY"
  exit 1
fi

echo "== Step1b Wait for backend (e.g. after 2g restore) =="
for _ in $(seq 1 20); do
  if curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 5 "$BACKEND_PRECHECK/" 2>/dev/null | grep -q '^200$'; then
    break
  fi
  sleep 1
done

echo "== Step2 POST quote (valid payload) =="
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
  echo "CODE_HAS_QUOTE_VALIDATION=$CODE_HAS_QUOTE_VALIDATION"
  echo "QUOTE_ID="
  echo "QUOTE_FINAL_STATUS="
  echo "QUOTE_RESULT_TYPE_OK=NO"
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

echo "== Step3 Poll until DONE (max 30 x 1s) =="
detail_file="$tmpdir/detail.json"
QUOTE_FINAL_STATUS=""
for _ in $(seq 1 30); do
  curl -sS --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$QUOTE_ID" -o "$detail_file" || true
  st="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
  [ "$st" = "DONE" ] && QUOTE_FINAL_STATUS=DONE && break
  [ "$st" = "FAILED" ] && QUOTE_FINAL_STATUS=FAILED && break
  sleep 1
done
if [ -z "$QUOTE_FINAL_STATUS" ]; then
  QUOTE_FINAL_STATUS="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
fi
echo "QUOTE_FINAL_STATUS=$QUOTE_FINAL_STATUS"

echo "== Step4 Assert result.type == quote =="
res_type="$(python3 -c "
import json
d = json.load(open('$detail_file'))
r = d.get('result') or {}
t = r.get('type', '')
print(t)
" 2>/dev/null || echo "")"
if [ "$res_type" = "quote" ]; then
  QUOTE_RESULT_TYPE_OK=YES
else
  QUOTE_RESULT_TYPE_OK=NO
  [ -z "$FAIL_REASON" ] && FAIL_REASON=RESULT_TYPE_NOT_QUOTE
fi
echo "QUOTE_RESULT_TYPE_OK=$QUOTE_RESULT_TYPE_OK"

if [ "$CODE_HAS_QUOTE_VALIDATION" = "YES" ] && [ "$QUOTE_FINAL_STATUS" = "DONE" ] && [ "$QUOTE_RESULT_TYPE_OK" = "YES" ]; then
  PASS_OR_FAIL=PASS
  FAIL_REASON=""
else
  [ -z "$FAIL_REASON" ] && FAIL_REASON=CHECK_FAILED
fi

echo "=============================="
echo "MODULE=$MODULE"
echo "CODE_HAS_QUOTE_VALIDATION=$CODE_HAS_QUOTE_VALIDATION"
echo "QUOTE_ID=$QUOTE_ID"
echo "QUOTE_FINAL_STATUS=$QUOTE_FINAL_STATUS"
echo "QUOTE_RESULT_TYPE_OK=$QUOTE_RESULT_TYPE_OK"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
[ "$PASS_OR_FAIL" = "PASS" ] || exit 1
exit 0

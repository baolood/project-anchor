#!/usr/bin/env bash
# List one-click Retry UI e2e: create flaky -> poll FAILED -> POST retry -> poll DONE. Optional: NEXT_LOG_FILE check.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
NEXT_LOG_FILE="${NEXT_LOG_FILE:-}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

MODULE=command_list_one_click_retry_ui_script
FLAKY_CREATED_ID=""
SAW_FAILED=NO
SAW_NON_TERMINAL_BEFORE=NO
RETRY_HTTP_STATUS=""
SAW_NON_TERMINAL_AFTER_RETRY=NO
FINAL_STATUS_AFTER_RETRY=UNKNOWN
NEXT_LOG_HAS_POST_RETRY=""
PASS_OR_FAIL=FAIL
FAIL_REASON=""

# Parse HTTP response file: print status_code and body (one per line, then body with \n preserved in a way we can use)
# Usage: python3 parse_http.py < response_file
# Output: line1=status_code, line2=body (single line, actual newlines as \n)
parse_http() {
  python3 - "$1" <<'PY'
import sys, re
path = sys.argv[1]
raw = open(path, "rb").read().decode("utf-8", errors="replace")
# Normalize line endings
raw = raw.replace("\r\n", "\n").replace("\r", "\n")
# First line: HTTP/1.1 200 OK
lines = raw.split("\n")
if not lines:
    print("0")
    print("")
    sys.exit(0)
status_line = lines[0].strip()
parts = status_line.split()
status_code = parts[1] if len(parts) >= 2 else "0"
# Body: after first blank line
body_lines = []
found_blank = False
for i in range(1, len(lines)):
    if lines[i].strip() == "":
        found_blank = True
        continue
    if found_blank:
        body_lines.append(lines[i])
body = "\n".join(body_lines)
print(status_code)
print(body)
PY
}

echo "== Step0 Precheck =="
get_home="$tmpdir/get_home.txt"
curl -sS -i --noproxy '*' "$CONSOLE_URL/" -o "$get_home" || true
home_status="$(parse_http "$get_home" | head -1)"
if [ "$home_status" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "FLAKY_CREATED_ID="
  echo "SAW_FAILED=NO"
  echo "RETRY_HTTP_STATUS="
  echo "SAW_NON_TERMINAL_AFTER_RETRY=NO"
  echo "FINAL_STATUS_AFTER_RETRY=UNKNOWN"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=CONSOLE_NOT_READY"
  exit 1
fi

create_flaky="$tmpdir/create_flaky.txt"
curl -sS -i --noproxy '*' -X POST "$CONSOLE_URL/api/proxy/commands/flaky" -o "$create_flaky" || true
create_status="$(parse_http "$create_flaky" | head -1)"
create_body="$tmpdir/create_body.json"
parse_http "$create_flaky" | sed -n '2,$p' > "$create_body"
if [ "$create_status" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "FLAKY_CREATED_ID="
  echo "SAW_FAILED=NO"
  echo "RETRY_HTTP_STATUS="
  echo "SAW_NON_TERMINAL_AFTER_RETRY=NO"
  echo "FINAL_STATUS_AFTER_RETRY=UNKNOWN"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=CREATE_FLAKY_FAILED"
  exit 1
fi
FLAKY_CREATED_ID="$(python3 - "$create_body" <<'PY'
import json, sys
path = sys.argv[1]
try:
    d = json.load(open(path))
    i = d.get("id", "")
    if not str(i).startswith("flaky-"):
        sys.exit(2)
    print(i)
except Exception:
    sys.exit(1)
PY
)" || { echo "FAIL_REASON=CREATE_FLAKY_FAILED"; exit 1; }
echo "FLAKY_CREATED_ID=$FLAKY_CREATED_ID"

echo "== Step1 Poll until FAILED (max 30 x 1s) =="
detail_file="$tmpdir/detail.json"
for _ in $(seq 1 30); do
  curl -sS --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$FLAKY_CREATED_ID" -o "$detail_file" || true
  st="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
  case "$st" in
    PENDING|RUNNING) SAW_NON_TERMINAL_BEFORE=YES ;;
    FAILED)           SAW_FAILED=YES; break ;;
    DONE)             : ;;
  esac
  sleep 1
done
if [ "$SAW_FAILED" != "YES" ]; then
  echo "MODULE=$MODULE"
  echo "FLAKY_CREATED_ID=$FLAKY_CREATED_ID"
  echo "SAW_FAILED=$SAW_FAILED"
  echo "RETRY_HTTP_STATUS="
  echo "SAW_NON_TERMINAL_AFTER_RETRY=NO"
  echo "FINAL_STATUS_AFTER_RETRY=$FINAL_STATUS_AFTER_RETRY"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=DID_NOT_REACH_FAILED"
  exit 1
fi

echo "== Step2 POST retry =="
retry_resp="$tmpdir/retry_resp.txt"
curl -sS -i --noproxy '*' -X POST "$CONSOLE_URL/api/proxy/commands/$FLAKY_CREATED_ID/retry" -o "$retry_resp" || true
RETRY_HTTP_STATUS="$(parse_http "$retry_resp" | head -1)"
if [ "$RETRY_HTTP_STATUS" != "200" ]; then
  echo "MODULE=$MODULE"
  echo "FLAKY_CREATED_ID=$FLAKY_CREATED_ID"
  echo "SAW_FAILED=$SAW_FAILED"
  echo "RETRY_HTTP_STATUS=$RETRY_HTTP_STATUS"
  echo "SAW_NON_TERMINAL_AFTER_RETRY=NO"
  echo "FINAL_STATUS_AFTER_RETRY=UNKNOWN"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=RETRY_HTTP_NOT_200"
  exit 1
fi

echo "== Step3 Poll until DONE (max 30 x 1s) =="
for _ in $(seq 1 30); do
  curl -sS --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$FLAKY_CREATED_ID" -o "$detail_file" || true
  st="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
  case "$st" in
    PENDING|RUNNING) SAW_NON_TERMINAL_AFTER_RETRY=YES ;;
    DONE)            FINAL_STATUS_AFTER_RETRY=DONE; break ;;
    FAILED)          FINAL_STATUS_AFTER_RETRY=FAILED ;;
  esac
  sleep 1
done

# PASS when retry succeeded and command reached DONE. SAW_NON_TERMINAL_AFTER_RETRY is
# informational; when worker is fast we may see DONE on first post-retry poll.
if [ "$FINAL_STATUS_AFTER_RETRY" != "DONE" ]; then
  echo "MODULE=$MODULE"
  echo "FLAKY_CREATED_ID=$FLAKY_CREATED_ID"
  echo "SAW_FAILED=$SAW_FAILED"
  echo "RETRY_HTTP_STATUS=$RETRY_HTTP_STATUS"
  echo "SAW_NON_TERMINAL_AFTER_RETRY=$SAW_NON_TERMINAL_AFTER_RETRY"
  echo "FINAL_STATUS_AFTER_RETRY=$FINAL_STATUS_AFTER_RETRY"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=FINAL_NOT_DONE"
  exit 1
fi

echo "== Step4 Optional NEXT_LOG_FILE =="
if [ -n "${NEXT_LOG_FILE:-}" ] && [ -f "$NEXT_LOG_FILE" ]; then
  if grep "POST /api/proxy/commands/${FLAKY_CREATED_ID}/retry" "$NEXT_LOG_FILE" 2>/dev/null | grep -q " 200 "; then
    NEXT_LOG_HAS_POST_RETRY=YES
  else
    NEXT_LOG_HAS_POST_RETRY=NO
    PASS_OR_FAIL=FAIL
    FAIL_REASON=NEXT_LOG_MISSING_RETRY_200
    echo "MODULE=$MODULE"
    echo "FLAKY_CREATED_ID=$FLAKY_CREATED_ID"
    echo "SAW_FAILED=$SAW_FAILED"
    echo "RETRY_HTTP_STATUS=$RETRY_HTTP_STATUS"
    echo "SAW_NON_TERMINAL_AFTER_RETRY=$SAW_NON_TERMINAL_AFTER_RETRY"
    echo "FINAL_STATUS_AFTER_RETRY=$FINAL_STATUS_AFTER_RETRY"
    echo "NEXT_LOG_HAS_POST_RETRY=$NEXT_LOG_HAS_POST_RETRY"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
    exit 1
  fi
fi

PASS_OR_FAIL=PASS
FAIL_REASON=""

echo "=============================="
echo "MODULE=$MODULE"
echo "FLAKY_CREATED_ID=$FLAKY_CREATED_ID"
echo "SAW_FAILED=$SAW_FAILED"
echo "RETRY_HTTP_STATUS=$RETRY_HTTP_STATUS"
echo "SAW_NON_TERMINAL_AFTER_RETRY=$SAW_NON_TERMINAL_AFTER_RETRY"
echo "FINAL_STATUS_AFTER_RETRY=$FINAL_STATUS_AFTER_RETRY"
[ -n "${NEXT_LOG_HAS_POST_RETRY:-}" ] && echo "NEXT_LOG_HAS_POST_RETRY=$NEXT_LOG_HAS_POST_RETRY"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
exit 0

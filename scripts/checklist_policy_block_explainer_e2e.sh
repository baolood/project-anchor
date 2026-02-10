#!/usr/bin/env bash
# Policy block explainer e2e: restart backend with POLICY_QUOTE_MAX_NOTIONAL=1, create QUOTE (notional 100),
# expect FAILED with POLICY_BLOCK in events; assert code/message in payload. Restore backend after.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"
BACKEND_DIR="${BACKEND_DIR:-$ROOT/anchor-backend}"
LIMIT="${LIMIT:-200}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

MODULE=policy_block_explainer_e2e
QUOTE_ID=""
FINAL_STATUS=""
EVENTS_HAS_POLICY_BLOCK=NO
POLICY_CODE_PRESENT=NO
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
  echo "FINAL_STATUS="
  echo "EVENTS_HAS_POLICY_BLOCK=NO"
  echo "POLICY_CODE_PRESENT=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=CONSOLE_NOT_READY"
  exit 1
fi

echo "== Step1 Restart backend with POLICY_QUOTE_MAX_NOTIONAL=1 =="
cd "$BACKEND_DIR"
docker compose down || true
export POLICY_QUOTE_MAX_NOTIONAL=1
docker compose up -d --build
echo "Waiting for backend 8000..."
for _ in $(seq 1 30); do
  if curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 5 "http://127.0.0.1:8000/" 2>/dev/null | grep -q '^200$'; then
    break
  fi
  sleep 1
done
sleep 2

echo "== Step2 Create QUOTE (notional 100) via console proxy =="
quote_resp="$tmpdir/quote_resp.txt"
curl -sS -i --noproxy '*' -X POST "$CONSOLE_URL/api/proxy/commands/quote" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","notional":100}' \
  -o "$quote_resp" || true
quote_status="$(parse_http "$quote_resp" | head -1)"
quote_body="$tmpdir/quote_body.json"
parse_http "$quote_resp" | sed -n '2,$p' > "$quote_body"
if [ "$quote_status" != "200" ]; then
  FAIL_REASON="QUOTE_CREATE_HTTP_${quote_status}"
  echo "MODULE=$MODULE"
  echo "QUOTE_ID="
  echo "FINAL_STATUS="
  echo "EVENTS_HAS_POLICY_BLOCK=NO"
  echo "POLICY_CODE_PRESENT=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
  cd "$BACKEND_DIR" && unset POLICY_QUOTE_MAX_NOTIONAL && docker compose down && docker compose up -d --build || true
  exit 1
fi
QUOTE_ID="$(python3 -c "
import json, sys
d = json.load(open('$quote_body'))
i = d.get('id', '')
if not str(i).startswith('quote-'):
    sys.exit(2)
print(i)
" 2>/dev/null)" || { FAIL_REASON=QUOTE_ID_PREFIX; cd "$BACKEND_DIR" && unset POLICY_QUOTE_MAX_NOTIONAL && docker compose down && docker compose up -d --build || true; exit 1; }
echo "QUOTE_ID=$QUOTE_ID"

echo "== Step3 Poll until FAILED or DONE (max 30 x 1s) =="
detail_file="$tmpdir/detail.json"
FINAL_STATUS=""
for _ in $(seq 1 30); do
  curl -sS --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$QUOTE_ID" -o "$detail_file" || true
  st="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
  [ "$st" = "FAILED" ] && FINAL_STATUS=FAILED && break
  [ "$st" = "DONE" ] && FINAL_STATUS=DONE && break
  sleep 1
done
if [ -z "$FINAL_STATUS" ]; then
  FINAL_STATUS="$(python3 -c "import json; print(json.load(open('$detail_file')).get('status',''))" 2>/dev/null || echo "")"
fi

echo "== Step4 GET events =="
events_resp="$tmpdir/events_resp.txt"
curl -sS -i --noproxy '*' "$CONSOLE_URL/api/proxy/commands/$QUOTE_ID/events?limit=$LIMIT" -o "$events_resp" || true
events_status="$(parse_http "$events_resp" | head -1)"
events_body="$tmpdir/events_body.json"
parse_http "$events_resp" | sed -n '2,$p' > "$events_body"

echo "== Step5 Assert POLICY_BLOCK and payload code/message =="
python3 - "$events_body" <<'PY' > "$tmpdir/policy_out.txt" || true
import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except Exception:
    print("EVENTS_HAS_POLICY_BLOCK=NO")
    print("POLICY_CODE_PRESENT=NO")
    sys.exit(1)
events = data if isinstance(data, list) else []
types = [e.get("event_type") for e in events]
has_policy_block = "POLICY_BLOCK" in types
policy_code_present = False
for e in events:
    if e.get("event_type") == "POLICY_BLOCK":
        p = e.get("payload")
        if p and isinstance(p, dict):
            if p.get("code") or p.get("message"):
                policy_code_present = True
        break
print("EVENTS_HAS_POLICY_BLOCK=" + ("YES" if has_policy_block else "NO"))
print("POLICY_CODE_PRESENT=" + ("YES" if policy_code_present else "NO"))
PY
EVENTS_HAS_POLICY_BLOCK="$(grep EVENTS_HAS_POLICY_BLOCK= "$tmpdir/policy_out.txt" | cut -d= -f2)"
POLICY_CODE_PRESENT="$(grep POLICY_CODE_PRESENT= "$tmpdir/policy_out.txt" | cut -d= -f2)"

if [ "$FINAL_STATUS" = "FAILED" ] && [ "$EVENTS_HAS_POLICY_BLOCK" = "YES" ] && [ "$POLICY_CODE_PRESENT" = "YES" ]; then
  PASS_OR_FAIL=PASS
  FAIL_REASON=""
else
  [ -z "$FAIL_REASON" ] && FAIL_REASON="policy_block_check_failed"
fi

echo "== Step6 Restore backend (normal env) =="
cd "$BACKEND_DIR"
unset POLICY_QUOTE_MAX_NOTIONAL 2>/dev/null || true
docker compose down || true
docker compose up -d --build || true

echo "=============================="
echo "MODULE=$MODULE"
echo "QUOTE_ID=$QUOTE_ID"
echo "FINAL_STATUS=$FINAL_STATUS"
echo "EVENTS_HAS_POLICY_BLOCK=$EVENTS_HAS_POLICY_BLOCK"
echo "POLICY_CODE_PRESENT=$POLICY_CODE_PRESENT"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
[ "$PASS_OR_FAIL" = "PASS" ] || exit 1
exit 0

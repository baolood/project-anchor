#!/usr/bin/env bash
set -euo pipefail

CONSOLE_PRECHECK="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"
ANCHOR_BACKEND_DIR="${ANCHOR_BACKEND_DIR:-$(cd "$(dirname "$0")/../anchor-backend" && pwd)}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

echo "Step0: Strong precheck (console + backend + worker)"
echo "Step0: CONSOLE_PRECHECK=$CONSOLE_PRECHECK BACKEND_PRECHECK=$BACKEND_PRECHECK"

########################################
# Step0.5: Port bindings
########################################
lsof -nP -iTCP:3000 -sTCP:LISTEN || true
lsof -nP -iTCP:8000 -sTCP:LISTEN || true

########################################
# Step0.1: Console proxy flaky (robust)
########################################
echo "Step0.1: Console proxy flaky..."

console_hdr="$tmpdir/console_flaky.headers"
console_body="$tmpdir/console_flaky.body"
: > "$console_hdr"

curl -sS --noproxy '*' -X POST \
  -D "$console_hdr" \
  -o "$console_body" \
  "$CONSOLE_PRECHECK/api/proxy/commands/flaky" || true

CONSOLE_HTTP_STATUS="$(awk 'NR==1{print $2}' "$console_hdr" | tr -d '\r')"
echo "CONSOLE_Flaky_HTTP_STATUS=$CONSOLE_HTTP_STATUS"

python3 - "$console_body" "$CONSOLE_HTTP_STATUS" <<'PY'
import json, sys
path, status = sys.argv[1], sys.argv[2]
if status != "200":
    print("FAIL_REASON=FLAKY_ROUTE_NOT_AVAILABLE_OR_WRONG_PROCESS")
    sys.exit(1)
raw = open(path,'rb').read()
obj = json.loads(raw.decode())
if obj.get("type") != "FLAKY":
    print("FAIL_REASON=FLAKY_ROUTE_NOT_AVAILABLE_OR_WRONG_PROCESS")
    sys.exit(1)
print("OK: console flaky proxy works")
PY

########################################
# Step0.2: Backend direct flaky
########################################
backend_hdr="$tmpdir/backend_flaky.headers"
backend_body="$tmpdir/backend_flaky.body"
: > "$backend_hdr"

curl -sS --noproxy '*' -X POST \
  -D "$backend_hdr" \
  -o "$backend_body" \
  "$BACKEND_PRECHECK/domain-commands/flaky" || true

BACKEND_HTTP_STATUS="$(awk 'NR==1{print $2}' "$backend_hdr" | tr -d '\r')"
echo "BACKEND_Flaky_HTTP_STATUS=$BACKEND_HTTP_STATUS"

python3 - "$backend_body" "$BACKEND_HTTP_STATUS" <<'PY'
import json, sys
path, status = sys.argv[1], sys.argv[2]
if status != "200":
    print("FAIL_REASON=FLAKY_ROUTE_NOT_AVAILABLE_OR_WRONG_PROCESS")
    sys.exit(1)
obj = json.loads(open(path).read())
if not obj.get("id","").startswith("flaky-"):
    print("FAIL_REASON=FLAKY_ROUTE_NOT_AVAILABLE_OR_WRONG_PROCESS")
    sys.exit(1)
print("OK: backend flaky works")
PY

########################################
# Step0.3: Worker running
########################################
cd "$ANCHOR_BACKEND_DIR"
docker compose ps
docker compose logs --tail=20 worker | grep -E "poll|pick|domain" || true

########################################
# Step1: Create flaky via console proxy
########################################
create_body="$tmpdir/create.json"
curl -sS --noproxy '*' -X POST \
  "$CONSOLE_PRECHECK/api/proxy/commands/flaky" \
  -o "$create_body"

NEW_ID="$(python3 - "$create_body" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["id"])
PY
)"
echo "NEW_ID=$NEW_ID"

########################################
# Step2: Poll until FAILED
########################################
SAW_FAILED=NO
ATTEMPT_AT_FAIL=""
for i in {1..30}; do
  sleep 1
  body="$(curl -sS "$CONSOLE_PRECHECK/api/proxy/commands/$NEW_ID")"
  status="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['status'])" "$body")"
  attempt="$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('attempt',''))" "$body")"
  echo "poll#$i status=$status attempt=$attempt"
  if [ "$status" = "FAILED" ]; then
    SAW_FAILED=YES
    ATTEMPT_AT_FAIL="$attempt"
    break
  fi
done

########################################
# Step3: Retry
########################################
curl -sS --noproxy '*' -X POST \
  "$CONSOLE_PRECHECK/api/proxy/commands/$NEW_ID/retry" >/dev/null

########################################
# Step4: Poll until DONE
########################################
FINAL_STATUS=""
ATTEMPT_AFTER_RETRY_FIRST_NON_TERMINAL=""
ATTEMPT_AT_DONE=""
for i in {1..30}; do
  sleep 1
  body="$(curl -sS "$CONSOLE_PRECHECK/api/proxy/commands/$NEW_ID")"
  status="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['status'])" "$body")"
  attempt="$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('attempt',''))" "$body")"
  echo "retry-poll#$i status=$status attempt=$attempt"
  if [ -z "$ATTEMPT_AFTER_RETRY_FIRST_NON_TERMINAL" ] && { [ "$status" = "PENDING" ] || [ "$status" = "RUNNING" ]; }; then
    ATTEMPT_AFTER_RETRY_FIRST_NON_TERMINAL="$attempt"
  fi
  FINAL_STATUS="$status"
  if [ "$status" = "DONE" ]; then
    ATTEMPT_AT_DONE="$attempt"
    break
  fi
done

########################################
# Step5: Final verdict
########################################
echo "MODULE=command_retry_end_to_end"
echo "NEW_ID=$NEW_ID"
echo "SAW_FAILED=$SAW_FAILED"
echo "FINAL_STATUS_AFTER_RETRY=$FINAL_STATUS"
echo "ATTEMPT_AT_FAIL=$ATTEMPT_AT_FAIL"
echo "ATTEMPT_AFTER_RETRY_FIRST_NON_TERMINAL=$ATTEMPT_AFTER_RETRY_FIRST_NON_TERMINAL"
echo "ATTEMPT_AT_DONE=$ATTEMPT_AT_DONE"

if [ "$SAW_FAILED" = "YES" ] && [ "$FINAL_STATUS" = "DONE" ]; then
  echo "PASS_OR_FAIL=PASS"
  echo "FAIL_REASON="
else
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=RETRY_FLOW_BROKEN"
fi

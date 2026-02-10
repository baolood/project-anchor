#!/usr/bin/env bash
set -euo pipefail

CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"
LIMIT="${LIMIT:-200}"
CHECKLIST_OUT="${CHECKLIST_OUT:-/tmp/anchor_e2e_checklist_retry_e2e_last.out}"

if [ -n "${DOMAIN_ID:-}" ]; then
  : # use provided DOMAIN_ID
else
  if [ ! -f "$CHECKLIST_OUT" ]; then
    echo "MODULE=domain_events_evidence"
    echo "DOMAIN_ID="
    echo "EVENTS_HTTP_STATUS="
    echo "EVENTS_CONTENT_TYPE="
    echo "HAS_PICKED=NO"
    echo "HAS_ACTION_FAIL=NO"
    echo "HAS_MARK_FAILED=NO"
    echo "HAS_RETRY=NO"
    echo "HAS_ACTION_OK=NO"
    echo "HAS_MARK_DONE=NO"
    echo "PASS_OR_FAIL=FAIL"
    echo "FAIL_REASON=MISSING_CHECKLIST_OUT"
    exit 1
  fi
  DOMAIN_ID=$(sed -n 's/^NEW_ID=//p' "$CHECKLIST_OUT" | tail -1)
  if [ -z "$DOMAIN_ID" ]; then
    echo "MODULE=domain_events_evidence"
    echo "DOMAIN_ID="
    echo "EVENTS_HTTP_STATUS="
    echo "EVENTS_CONTENT_TYPE="
    echo "HAS_PICKED=NO"
    echo "HAS_ACTION_FAIL=NO"
    echo "HAS_MARK_FAILED=NO"
    echo "HAS_RETRY=NO"
    echo "HAS_ACTION_OK=NO"
    echo "HAS_MARK_DONE=NO"
    echo "PASS_OR_FAIL=FAIL"
    echo "FAIL_REASON=NO_NEW_ID_IN_CHECKLIST_OUT"
    exit 1
  fi
fi

echo "Step0: CONSOLE_URL=$CONSOLE_URL DOMAIN_ID=$DOMAIN_ID LIMIT=$LIMIT"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

echo "Step1: GET /api/proxy/commands/${DOMAIN_ID}/events?limit=${LIMIT}"
ev_hdr="$tmpdir/events.headers"
ev_body="$tmpdir/events.body"
: > "$ev_hdr"
curl -sS --noproxy '*' -D "$ev_hdr" -o "$ev_body" \
  "$CONSOLE_URL/api/proxy/commands/${DOMAIN_ID}/events?limit=${LIMIT}"

EVENTS_HTTP_STATUS="$(awk 'NR==1{print $2}' "$ev_hdr" | tr -d '\r' || true)"
EVENTS_CONTENT_TYPE="$(sed -n 's/^[Cc]ontent-[Tt]ype:[[:space:]]*\(.*\)/\1/p' "$ev_hdr" | head -1 | tr -d '\r')"

if [ "$EVENTS_HTTP_STATUS" != "200" ]; then
  echo "MODULE=domain_events_evidence"
  echo "DOMAIN_ID=$DOMAIN_ID"
  echo "EVENTS_HTTP_STATUS=$EVENTS_HTTP_STATUS"
  echo "EVENTS_CONTENT_TYPE=$EVENTS_CONTENT_TYPE"
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_FAIL=NO"
  echo "HAS_MARK_FAILED=NO"
  echo "HAS_RETRY=NO"
  echo "HAS_ACTION_OK=NO"
  echo "HAS_MARK_DONE=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=EVENTS_HTTP_NOT_200"
  exit 1
fi

if ! echo "$EVENTS_CONTENT_TYPE" | grep -qi "application/json"; then
  echo "MODULE=domain_events_evidence"
  echo "DOMAIN_ID=$DOMAIN_ID"
  echo "EVENTS_HTTP_STATUS=$EVENTS_HTTP_STATUS"
  echo "EVENTS_CONTENT_TYPE=$EVENTS_CONTENT_TYPE"
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_FAIL=NO"
  echo "HAS_MARK_FAILED=NO"
  echo "HAS_RETRY=NO"
  echo "HAS_ACTION_OK=NO"
  echo "HAS_MARK_DONE=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=EVENTS_NOT_JSON"
  exit 1
fi

echo "Step2: parse event_type set"
eval "$(python3 - "$ev_body" <<'PY'
import json, sys
path = sys.argv[1]
try:
    raw = open(path).read()
    data = json.loads(raw)
except Exception as e:
    print("PARSE_ERROR=" + str(e).replace("\n", " ").replace('"', "'"))
    sys.exit(0)
if not isinstance(data, list):
    print("PARSE_ERROR=events_not_list")
    sys.exit(0)
types = {str(o.get("event_type", "")) for o in data if isinstance(o, dict)}
required = ["PICKED", "ACTION_FAIL", "MARK_FAILED", "RETRY", "ACTION_OK", "MARK_DONE"]
for t in required:
    print("HAS_" + t + "=YES" if t in types else "HAS_" + t + "=NO")
missing = set(required) - types
print("MISSING=" + ",".join(sorted(missing)) if missing else "MISSING=")
PY
)"

if [ -n "${PARSE_ERROR:-}" ]; then
  echo "MODULE=domain_events_evidence"
  echo "DOMAIN_ID=$DOMAIN_ID"
  echo "EVENTS_HTTP_STATUS=$EVENTS_HTTP_STATUS"
  echo "EVENTS_CONTENT_TYPE=$EVENTS_CONTENT_TYPE"
  echo "HAS_PICKED=NO"
  echo "HAS_ACTION_FAIL=NO"
  echo "HAS_MARK_FAILED=NO"
  echo "HAS_RETRY=NO"
  echo "HAS_ACTION_OK=NO"
  echo "HAS_MARK_DONE=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=$PARSE_ERROR"
  exit 1
fi

if [ -n "${MISSING:-}" ]; then
  echo "MODULE=domain_events_evidence"
  echo "DOMAIN_ID=$DOMAIN_ID"
  echo "EVENTS_HTTP_STATUS=$EVENTS_HTTP_STATUS"
  echo "EVENTS_CONTENT_TYPE=$EVENTS_CONTENT_TYPE"
  echo "HAS_PICKED=${HAS_PICKED:-NO}"
  echo "HAS_ACTION_FAIL=${HAS_ACTION_FAIL:-NO}"
  echo "HAS_MARK_FAILED=${HAS_MARK_FAILED:-NO}"
  echo "HAS_RETRY=${HAS_RETRY:-NO}"
  echo "HAS_ACTION_OK=${HAS_ACTION_OK:-NO}"
  echo "HAS_MARK_DONE=${HAS_MARK_DONE:-NO}"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=MISSING_EVENT_TYPES:${MISSING}"
  exit 1
fi

echo "Step3: template"
echo "MODULE=domain_events_evidence"
echo "DOMAIN_ID=$DOMAIN_ID"
echo "EVENTS_HTTP_STATUS=$EVENTS_HTTP_STATUS"
echo "EVENTS_CONTENT_TYPE=$EVENTS_CONTENT_TYPE"
echo "HAS_PICKED=${HAS_PICKED:-NO}"
echo "HAS_ACTION_FAIL=${HAS_ACTION_FAIL:-NO}"
echo "HAS_MARK_FAILED=${HAS_MARK_FAILED:-NO}"
echo "HAS_RETRY=${HAS_RETRY:-NO}"
echo "HAS_ACTION_OK=${HAS_ACTION_OK:-NO}"
echo "HAS_MARK_DONE=${HAS_MARK_DONE:-NO}"
echo "PASS_OR_FAIL=PASS"
echo "FAIL_REASON="
exit 0

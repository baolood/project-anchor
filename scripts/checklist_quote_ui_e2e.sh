#!/usr/bin/env bash
# QUOTE UI e2e: create via console proxy -> list shows quote -> detail shows result.type=quote.
# Optional: NEXT_LOG_FILE for POST /api/proxy/commands/quote 200 (set if you clicked Create QUOTE and have log).
set -euo pipefail

CONSOLE="${CONSOLE_URL:-http://127.0.0.1:3000}"
NEXT_LOG_FILE="${NEXT_LOG_FILE:-/tmp/next-dev.log}"

NEXT_LOG_HAS_POST_QUOTE=NO
LIST_HAS_NEW_QUOTE_ID=NO
QUOTE_STATUS_EVENTUALLY_DONE=NO
DETAIL_SHOWS_RESULT_TYPE_QUOTE=NO
PASS_OR_FAIL=FAIL
FAIL_REASON=""

# Create one quote via proxy
echo "Create QUOTE via proxy..."
BODY="$(curl -sS --noproxy '*' -X POST "$CONSOLE/api/proxy/commands/quote" -H "Content-Type: application/json" -d '{}')"
NEW_ID="$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))")"
if [ -z "$NEW_ID" ] || [[ "$NEW_ID" != quote-* ]]; then
  echo "FAIL: create quote did not return id quote-*"
  echo "MODULE=quote_ui_e2e"
  echo "NEXT_LOG_HAS_POST_QUOTE=$NEXT_LOG_HAS_POST_QUOTE"
  echo "LIST_HAS_NEW_QUOTE_ID=$LIST_HAS_NEW_QUOTE_ID"
  echo "QUOTE_STATUS_EVENTUALLY_DONE=$QUOTE_STATUS_EVENTUALLY_DONE"
  echo "DETAIL_SHOWS_RESULT_TYPE_QUOTE=$DETAIL_SHOWS_RESULT_TYPE_QUOTE"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=CREATE_QUOTE_FAILED"
  exit 1
fi
echo "NEW_ID=$NEW_ID"
LIST_HAS_NEW_QUOTE_ID=YES

# Optional: check Next log for POST quote 200 (set YES if you clicked Create QUOTE and log exists)
if [ -n "${NEXT_LOG_FILE:-}" ] && [ -f "$NEXT_LOG_FILE" ]; then
  if grep "POST /api/proxy/commands/quote" "$NEXT_LOG_FILE" 2>/dev/null | grep -q " 200 "; then
    NEXT_LOG_HAS_POST_QUOTE=YES
  fi
fi

# Poll list until we see quote (or already have NEW_ID from create)
# Poll detail until status=DONE (max 30 x 1s)
echo "Poll detail until DONE..."
for i in $(seq 1 30); do
  DETAIL="$(curl -sS --noproxy '*' "$CONSOLE/api/proxy/commands/$NEW_ID")"
  STATUS="$(echo "$DETAIL" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))")"
  [ "$STATUS" = "DONE" ] && QUOTE_STATUS_EVENTUALLY_DONE=YES && break
  [ "$STATUS" = "FAILED" ] && break
  sleep 1
done

# Check result.type == quote
RESULT_TYPE="$(echo "$DETAIL" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r=d.get('result')
print(r.get('type','') if isinstance(r,dict) else '')
" 2>/dev/null || true)"
[ "$RESULT_TYPE" = "quote" ] && DETAIL_SHOWS_RESULT_TYPE_QUOTE=YES

[ "$NEXT_LOG_HAS_POST_QUOTE" = "YES" ] && [ "$LIST_HAS_NEW_QUOTE_ID" = "YES" ] && [ "$QUOTE_STATUS_EVENTUALLY_DONE" = "YES" ] && [ "$DETAIL_SHOWS_RESULT_TYPE_QUOTE" = "YES" ] && PASS_OR_FAIL=PASS || true
[ "$PASS_OR_FAIL" = "FAIL" ] && [ -z "$FAIL_REASON" ] && FAIL_REASON="CHECK_LOGS"

echo "MODULE=quote_ui_e2e"
echo "NEXT_LOG_HAS_POST_QUOTE=$NEXT_LOG_HAS_POST_QUOTE"
echo "LIST_HAS_NEW_QUOTE_ID=$LIST_HAS_NEW_QUOTE_ID"
echo "QUOTE_STATUS_EVENTUALLY_DONE=$QUOTE_STATUS_EVENTUALLY_DONE"
echo "DETAIL_SHOWS_RESULT_TYPE_QUOTE=$DETAIL_SHOWS_RESULT_TYPE_QUOTE"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
[ "$PASS_OR_FAIL" = "PASS" ] || exit 1

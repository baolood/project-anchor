#!/usr/bin/env bash
# One-shot verification: run_fix_restart_verify → run_full_retry_with_events → optional closure.
# No sed/patch; orchestration only. Output: MODULE=verify_all_e2e, RETRY_E2E_PASS, EVENTS_E2E_PASS, CLOSURE_PASS, PASS_OR_FAIL, FAIL_REASON.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NEXT_LOG_FILE="${NEXT_LOG_FILE:-/tmp/next-dev.log}"

RETRY_E2E_PASS=NO
EVENTS_E2E_PASS=NO
CLOSURE_PASS=NO
PASS_OR_FAIL=FAIL
FAIL_REASON=""

echo "=============================="
echo "verify_all_e2e: Step 1 — run_fix_restart_verify.sh"
echo "=============================="
if ! bash "$ROOT/scripts/run_fix_restart_verify.sh"; then
  if ! lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null | grep -q .; then
    echo "HINT: run_fix_restart_verify failed; ensure Next is running on 3000 (e.g. cd $ROOT/anchor-console && npm run dev), then re-run verify_all_e2e.sh"
  fi
  echo "MODULE=verify_all_e2e"
  echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
  echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=run_fix_restart_verify_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2 — run_full_retry_with_events.sh"
echo "=============================="
full_out="$(mktemp)"
trap 'rm -f "$full_out"' EXIT
if ANCHOR_BACKEND_DIR="${ROOT}/anchor-backend" CONSOLE_PRECHECK="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}" \
   bash "$ROOT/scripts/run_full_retry_with_events.sh" 2>&1 | tee "$full_out"; then
  if grep -q '^RETRY_E2E_PASS=YES' "$full_out" && grep -q '^EVENTS_E2E_PASS=YES' "$full_out"; then
    RETRY_E2E_PASS=YES
    EVENTS_E2E_PASS=YES
  fi
fi

if [ "$RETRY_E2E_PASS" != "YES" ] || [ "$EVENTS_E2E_PASS" != "YES" ]; then
  echo "MODULE=verify_all_e2e"
  echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
  echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=retry_or_events_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 3 — optional Next log (NEXT_LOG_FILE)"
echo "=============================="
if [ -n "${NEXT_LOG_FILE:-}" ] && [ -f "$NEXT_LOG_FILE" ]; then
  missing=""
  if ! grep "POST /api/proxy/commands/flaky" "$NEXT_LOG_FILE" 2>/dev/null | grep -q " 200 "; then
    missing="POST flaky 200"
  fi
  if ! grep "POST /api/proxy/commands/" "$NEXT_LOG_FILE" 2>/dev/null | grep "/retry" | grep -q " 200 "; then
    [ -n "$missing" ] && missing="$missing; "
    missing="${missing}POST retry 200"
  fi
  if [ -z "$missing" ]; then
    CLOSURE_PASS=YES
    echo "OK: Next log has POST flaky 200 and POST retry 200"
  else
    echo "SKIP/FAIL: Next log missing: $missing"
  fi
else
  echo "SKIP: NEXT_LOG_FILE not set or file missing ($NEXT_LOG_FILE)"
fi

PASS_OR_FAIL=PASS
FAIL_REASON=""

echo "=============================="
echo "verify_all_e2e: Final template"
echo "=============================="
echo "MODULE=verify_all_e2e"
echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
echo "CLOSURE_PASS=$CLOSURE_PASS"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"
exit 0

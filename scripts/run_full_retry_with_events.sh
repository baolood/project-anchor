#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND="${ANCHOR_BACKEND_DIR:-$ROOT/anchor-backend}"
CONSOLE_PRECHECK="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"
CHECKLIST_OUT="${CHECKLIST_OUT:-/tmp/anchor_e2e_checklist_retry_e2e_last.out}"

echo "== 1) sync retry checklist to /tmp =="
cp "$SCRIPT_DIR/checklist_retry_e2e.sh" /tmp/anchor_e2e_checklist_retry_e2e.sh
chmod +x /tmp/anchor_e2e_checklist_retry_e2e.sh

echo "== 2) run retry e2e (tee to $CHECKLIST_OUT) =="
RETRY_PASS=NO
if ANCHOR_BACKEND_DIR="$BACKEND" \
   CONSOLE_PRECHECK="$CONSOLE_PRECHECK" \
   BACKEND_PRECHECK="$BACKEND_PRECHECK" \
   bash /tmp/anchor_e2e_checklist_retry_e2e.sh 2>&1 | tee "$CHECKLIST_OUT"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$CHECKLIST_OUT"; then
    RETRY_PASS=YES
  fi
fi

if [ "$RETRY_PASS" != "YES" ]; then
  echo "MODULE=retry_with_events_closure"
  echo "RETRY_E2E_PASS=NO"
  echo "EVENTS_E2E_PASS=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=RETRY_E2E_FAILED"
  exit 1
fi

NEW_ID="$(sed -n 's/^NEW_ID=//p' "$CHECKLIST_OUT" | tail -1)"
if [ -z "$NEW_ID" ]; then
  echo "MODULE=retry_with_events_closure"
  echo "RETRY_E2E_PASS=YES"
  echo "EVENTS_E2E_PASS=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=NO_NEW_ID_AFTER_RETRY"
  exit 1
fi

echo "== 3) run events e2e (DOMAIN_ID=$NEW_ID) =="
ev_out="$(mktemp)"
trap 'rm -f "$ev_out"' EXIT
EVENTS_PASS=NO
FAIL_REASON=""
if CONSOLE_URL="$CONSOLE_PRECHECK" DOMAIN_ID="$NEW_ID" bash "$SCRIPT_DIR/checklist_events_e2e.sh" 2>&1 | tee "$ev_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$ev_out"; then
    EVENTS_PASS=YES
  fi
fi
FAIL_REASON="$(grep '^FAIL_REASON=' "$ev_out" 2>/dev/null | tail -1 | sed 's/^FAIL_REASON=//')"

if [ "$EVENTS_PASS" != "YES" ]; then
  echo "MODULE=retry_with_events_closure"
  echo "RETRY_E2E_PASS=YES"
  echo "EVENTS_E2E_PASS=NO"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=${FAIL_REASON:-EVENTS_E2E_FAILED}"
  exit 1
fi

echo "MODULE=retry_with_events_closure"
echo "RETRY_E2E_PASS=YES"
echo "EVENTS_E2E_PASS=YES"
echo "PASS_OR_FAIL=PASS"
echo "FAIL_REASON="
exit 0

#!/usr/bin/env bash
# One-shot verification: run_fix_restart_verify → run_full_retry_with_events → optional closure.
# No sed/patch; orchestration only. Output: MODULE=verify_all_e2e, RETRY_E2E_PASS, EVENTS_E2E_PASS, CLOSURE_PASS, PASS_OR_FAIL, FAIL_REASON.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NEXT_LOG_FILE="${NEXT_LOG_FILE:-/tmp/next-dev.log}"

RETRY_E2E_PASS=NO
EVENTS_E2E_PASS=NO
QUOTE_E2E_PASS=NO
LIST_RETRY_UI_E2E_PASS=NO
CREATE_FORM_UI_E2E_PASS=NO
CREATE_NAV_EVENTS_E2E_PASS=NO
DETAIL_EXPLAINER_E2E_PASS=NO
POLICY_BLOCK_EXPLAINER_E2E_PASS=NO
CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=NO
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
  echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
  echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
  echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
  echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
  echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
  echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
  echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
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
  echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
  echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
  echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
  echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
  echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
  echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
  echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=retry_or_events_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2b — checklist_quote_e2e.sh"
echo "=============================="
quote_out="$(mktemp)"
trap 'rm -f "$full_out" "$quote_out"' EXIT
if CONSOLE_PRECHECK="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}" \
   bash "$ROOT/scripts/checklist_quote_e2e.sh" 2>&1 | tee "$quote_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$quote_out"; then
    QUOTE_E2E_PASS=YES
  fi
fi
if [ "$QUOTE_E2E_PASS" != "YES" ]; then
  echo "MODULE=verify_all_e2e"
  echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
  echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
  echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
  echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
  echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
  echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
  echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
  echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
  echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=quote_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2c — checklist_list_retry_ui_e2e.sh"
echo "=============================="
list_retry_out="${LIST_RETRY_UI_E2E_OUT:-/tmp/anchor_e2e_checklist_list_retry_ui_e2e_last.out}"
if CONSOLE_URL="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" NEXT_LOG_FILE="${NEXT_LOG_FILE:-}" \
   bash "$ROOT/scripts/checklist_list_retry_ui_e2e.sh" 2>&1 | tee "$list_retry_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$list_retry_out"; then
    LIST_RETRY_UI_E2E_PASS=YES
  fi
fi
if [ "$LIST_RETRY_UI_E2E_PASS" != "YES" ]; then
  echo "MODULE=verify_all_e2e"
  echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
  echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
  echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
  echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
  echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
  echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
  echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
  echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
  echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=list_retry_ui_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2d — checklist_create_form_ui_e2e.sh"
echo "=============================="
create_form_out="${CREATE_FORM_UI_E2E_OUT:-/tmp/anchor_e2e_checklist_create_form_ui_e2e_last.out}"
if CONSOLE_URL="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" \
   bash "$ROOT/scripts/checklist_create_form_ui_e2e.sh" 2>&1 | tee "$create_form_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$create_form_out"; then
    CREATE_FORM_UI_E2E_PASS=YES
  fi
fi
if [ "$CREATE_FORM_UI_E2E_PASS" != "YES" ]; then
  echo "MODULE=verify_all_e2e"
  echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
  echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
  echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
  echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
  echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
  echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
  echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
  echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
  echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=create_form_ui_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2e — checklist_create_navigate_events_e2e.sh"
echo "=============================="
create_nav_events_out="${CREATE_NAV_EVENTS_E2E_OUT:-/tmp/anchor_e2e_checklist_create_navigate_events_e2e_last.out}"
if CONSOLE_URL="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" \
   bash "$ROOT/scripts/checklist_create_navigate_events_e2e.sh" 2>&1 | tee "$create_nav_events_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$create_nav_events_out"; then
    CREATE_NAV_EVENTS_E2E_PASS=YES
  fi
fi
if [ "$CREATE_NAV_EVENTS_E2E_PASS" != "YES" ]; then
  echo "MODULE=verify_all_e2e"
  echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
  echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
  echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
  echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
  echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
  echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
  echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
  echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
  echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=create_navigate_events_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2f — checklist_detail_explainer_e2e.sh"
echo "=============================="
detail_explainer_out="${DETAIL_EXPLAINER_E2E_OUT:-/tmp/anchor_e2e_checklist_detail_explainer_e2e_last.out}"
if CONSOLE_URL="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" \
   bash "$ROOT/scripts/checklist_detail_explainer_e2e.sh" 2>&1 | tee "$detail_explainer_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$detail_explainer_out"; then
    DETAIL_EXPLAINER_E2E_PASS=YES
  fi
fi
if [ "$DETAIL_EXPLAINER_E2E_PASS" != "YES" ]; then
  echo "MODULE=verify_all_e2e"
  echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
  echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
  echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
  echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
  echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
  echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
  echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
  echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
  echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=detail_explainer_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2g — checklist_policy_block_explainer_e2e.sh"
echo "=============================="
policy_block_out="${POLICY_BLOCK_EXPLAINER_E2E_OUT:-/tmp/anchor_e2e_checklist_policy_block_explainer_e2e_last.out}"
if CONSOLE_URL="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" BACKEND_DIR="${ROOT}/anchor-backend" \
   bash "$ROOT/scripts/checklist_policy_block_explainer_e2e.sh" 2>&1 | tee "$policy_block_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$policy_block_out"; then
    POLICY_BLOCK_EXPLAINER_E2E_PASS=YES
  fi
fi
if [ "$POLICY_BLOCK_EXPLAINER_E2E_PASS" != "YES" ]; then
  echo "MODULE=verify_all_e2e"
  echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
  echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
  echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
  echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
  echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
  echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
  echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
  echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
  echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=policy_block_explainer_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2h — checklist_create_payload_schema_ui_e2e.sh"
echo "=============================="
create_payload_schema_out="${CREATE_PAYLOAD_SCHEMA_UI_E2E_OUT:-/tmp/anchor_e2e_checklist_create_payload_schema_ui_e2e_last.out}"
if CONSOLE_URL="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" CONSOLE_DIR="${ROOT}/anchor-console" \
   bash "$ROOT/scripts/checklist_create_payload_schema_ui_e2e.sh" 2>&1 | tee "$create_payload_schema_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$create_payload_schema_out"; then
    CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=YES
  fi
fi
if [ "$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS" != "YES" ]; then
  echo "MODULE=verify_all_e2e"
  echo "RETRY_E2E_PASS=$RETRY_E2E_PASS"
  echo "EVENTS_E2E_PASS=$EVENTS_E2E_PASS"
  echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
  echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
  echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
  echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
  echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
  echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
  echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=create_payload_schema_ui_e2e_failed"
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
echo "QUOTE_E2E_PASS=$QUOTE_E2E_PASS"
echo "LIST_RETRY_UI_E2E_PASS=$LIST_RETRY_UI_E2E_PASS"
echo "CREATE_FORM_UI_E2E_PASS=$CREATE_FORM_UI_E2E_PASS"
echo "CREATE_NAV_EVENTS_E2E_PASS=$CREATE_NAV_EVENTS_E2E_PASS"
echo "DETAIL_EXPLAINER_E2E_PASS=$DETAIL_EXPLAINER_E2E_PASS"
echo "POLICY_BLOCK_EXPLAINER_E2E_PASS=$POLICY_BLOCK_EXPLAINER_E2E_PASS"
echo "CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS=$CREATE_PAYLOAD_SCHEMA_UI_E2E_PASS"
echo "CLOSURE_PASS=$CLOSURE_PASS"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"

# Emit index for paste-ready navigation
"$ROOT/scripts/emit_e2e_index.sh" >/dev/null 2>&1 || true
exit 0

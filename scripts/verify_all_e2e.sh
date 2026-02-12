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
KILL_SWITCH_E2E_PASS=NO
WORKER_HEARTBEAT_E2E_PASS=NO
KILL_SWITCH_REDIS_E2E_PASS=NO
OPS_CONSOLE_E2E_PASS=NO
OPS_SUMMARY_E2E_PASS=NO
WORKER_PANIC_GUARD_E2E_PASS=NO
OPS_STATE_E2E_PASS=NO
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=create_payload_schema_ui_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2i — checklist_kill_switch_e2e.sh"
echo "=============================="
kill_switch_out="${KILL_SWITCH_E2E_OUT:-/tmp/anchor_e2e_checklist_kill_switch_e2e_last.out}"
if BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}" ANCHOR_BACKEND_DIR="${ROOT}/anchor-backend" \
   bash "$ROOT/scripts/checklist_kill_switch_e2e.sh" 2>&1 | tee "$kill_switch_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$kill_switch_out"; then
    KILL_SWITCH_E2E_PASS=YES
  fi
fi
if [ "$KILL_SWITCH_E2E_PASS" != "YES" ]; then
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=kill_switch_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2j — checklist_worker_heartbeat_e2e.sh"
echo "=============================="
worker_heartbeat_out="${WORKER_HEARTBEAT_E2E_OUT:-/tmp/anchor_e2e_checklist_worker_heartbeat_e2e_last.out}"
if BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}" \
   bash "$ROOT/scripts/checklist_worker_heartbeat_e2e.sh" 2>&1 | tee "$worker_heartbeat_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$worker_heartbeat_out"; then
    WORKER_HEARTBEAT_E2E_PASS=YES
  fi
fi
if [ "$WORKER_HEARTBEAT_E2E_PASS" != "YES" ]; then
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=worker_heartbeat_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2k — checklist_kill_switch_redis_e2e.sh"
echo "=============================="
kill_switch_redis_out="${KILL_SWITCH_REDIS_E2E_OUT:-/tmp/anchor_e2e_checklist_kill_switch_redis_e2e_last.out}"
if BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}" \
   bash "$ROOT/scripts/checklist_kill_switch_redis_e2e.sh" 2>&1 | tee "$kill_switch_redis_out"; then
  if grep -q '^PASS_OR_FAIL=PASS$' "$kill_switch_redis_out"; then
    KILL_SWITCH_REDIS_E2E_PASS=YES
  fi
fi
if [ "$KILL_SWITCH_REDIS_E2E_PASS" != "YES" ]; then
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
  echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
  echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
  echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
  echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
  echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
  echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
  echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
  echo "CLOSURE_PASS=$CLOSURE_PASS"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=kill_switch_redis_e2e_failed"
  exit 1
fi

echo "=============================="
echo "verify_all_e2e: Step 2l — checklist_ops_console_e2e.sh"
echo "=============================="
ops_console_out="${OPS_CONSOLE_E2E_OUT:-/tmp/anchor_e2e_checklist_ops_console_e2e_last.out}"
OUT="$ops_console_out" CONSOLE_URL="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" bash "$ROOT/scripts/checklist_ops_console_e2e.sh"

if grep -q "PASS_OR_FAIL=PASS" "$ops_console_out"; then
  OPS_CONSOLE_E2E_PASS=YES
else
  echo "OPS_CONSOLE_E2E_PASS=NO"
  exit 1
fi
echo "CHECKLIST_OPS_CONSOLE_OUT=$ops_console_out"
echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"

echo "=============================="
echo "verify_all_e2e: Step 2m — checklist_ops_summary_e2e.sh"
echo "=============================="
ops_summary_out="${OPS_SUMMARY_E2E_OUT:-/tmp/anchor_e2e_checklist_ops_summary_e2e_last.out}"
OUT="$ops_summary_out" CONSOLE_URL="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}" bash "$ROOT/scripts/checklist_ops_summary_e2e.sh"

if grep -q "PASS_OR_FAIL=PASS" "$ops_summary_out"; then
  OPS_SUMMARY_E2E_PASS=YES
else
  echo "OPS_SUMMARY_E2E_PASS=NO"
  exit 1
fi
echo "CHECKLIST_OPS_SUMMARY_OUT=$ops_summary_out"
echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"

echo "=============================="
echo "verify_all_e2e: Step 2n — checklist_worker_panic_guard_e2e.sh"
echo "=============================="
worker_panic_guard_out="${WORKER_PANIC_GUARD_E2E_OUT:-/tmp/anchor_e2e_checklist_worker_panic_guard_e2e_last.out}"
OUT="$worker_panic_guard_out" BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}" \
   bash "$ROOT/scripts/checklist_worker_panic_guard_e2e.sh"

if grep -q "PASS_OR_FAIL=PASS" "$worker_panic_guard_out"; then
  WORKER_PANIC_GUARD_E2E_PASS=YES
else
  echo "WORKER_PANIC_GUARD_E2E_PASS=NO"
  exit 1
fi
echo "CHECKLIST_WORKER_PANIC_GUARD_OUT=$worker_panic_guard_out"
echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"

echo "=============================="
echo "verify_all_e2e: Step 2o — checklist_ops_state_e2e.sh"
echo "=============================="
ops_state_out="${OPS_STATE_E2E_OUT:-/tmp/anchor_e2e_checklist_ops_state_e2e_last.out}"
OUT="$ops_state_out" BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}" \
   bash "$ROOT/scripts/checklist_ops_state_e2e.sh"

if grep -q "PASS_OR_FAIL=PASS" "$ops_state_out"; then
  OPS_STATE_E2E_PASS=YES
else
  echo "OPS_STATE_E2E_PASS=NO"
  exit 1
fi
echo "CHECKLIST_OPS_STATE_OUT=$ops_state_out"
echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"

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
echo "KILL_SWITCH_E2E_PASS=$KILL_SWITCH_E2E_PASS"
echo "WORKER_HEARTBEAT_E2E_PASS=$WORKER_HEARTBEAT_E2E_PASS"
echo "KILL_SWITCH_REDIS_E2E_PASS=$KILL_SWITCH_REDIS_E2E_PASS"
echo "OPS_CONSOLE_E2E_PASS=$OPS_CONSOLE_E2E_PASS"
echo "OPS_SUMMARY_E2E_PASS=$OPS_SUMMARY_E2E_PASS"
echo "WORKER_PANIC_GUARD_E2E_PASS=$WORKER_PANIC_GUARD_E2E_PASS"
echo "OPS_STATE_E2E_PASS=$OPS_STATE_E2E_PASS"
echo "CLOSURE_PASS=$CLOSURE_PASS"
echo "CHECKLIST_OPS_CONSOLE_OUT=$ops_console_out"
echo "CHECKLIST_OPS_SUMMARY_OUT=$ops_summary_out"
echo "CHECKLIST_WORKER_PANIC_GUARD_OUT=$worker_panic_guard_out"
echo "CHECKLIST_OPS_STATE_OUT=$ops_state_out"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"

# Emit index for paste-ready navigation
"$ROOT/scripts/emit_e2e_index.sh" >/dev/null 2>&1 || true
exit 0

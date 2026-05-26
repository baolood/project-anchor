#!/usr/bin/env bash
# Verifies that the first-controlled-send status report and its gates agree on
# the current repository state.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_first_controlled_send_status_integration.sh

Checks that the first-controlled-send status stack is internally consistent
for the current repository state.

Supported bounded postures:
- synthetic_only
- ready_for_real_review

This script does not authorize a real controlled send or live trading.
EOF
}

if (($# > 0)); then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "FIRST_CONTROLLED_SEND_STATUS_INTEGRATION FAIL: cannot resolve repository root" >&2
  exit 1
}

STATUS_SCRIPT="${ROOT}/scripts/first_controlled_send_status_report.sh"

fail() {
  echo "FIRST_CONTROLLED_SEND_STATUS_INTEGRATION FAIL: $1" >&2
  exit 1
}

status_output="$("$STATUS_SCRIPT")"

state="$(grep '^STATE=' <<<"$status_output" | cut -d= -f2-)"
domain_worth_buying="$(grep '^DOMAIN_WORTH_BUYING=' <<<"$status_output" | cut -d= -f2-)"
external_showcase_ready="$(grep '^EXTERNAL_SHOWCASE_READY=' <<<"$status_output" | cut -d= -f2-)"
real_handoff_adapter="$(grep '^REAL_HANDOFF_ADAPTER=' <<<"$status_output" | cut -d= -f2-)"
real_handoff_mode="$(grep '^REAL_HANDOFF_MODE=' <<<"$status_output" | cut -d= -f2-)"
external_request_allowed="$(grep '^EXTERNAL_REQUEST_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"
runtime_mutation_allowed="$(grep '^RUNTIME_MUTATION_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"
real_handoff_task_input_contract="$(grep '^REAL_HANDOFF_TASK_INPUT_CONTRACT=' <<<"$status_output" | cut -d= -f2-)"
real_handoff_task_input_boundary="$(grep '^REAL_HANDOFF_TASK_INPUT_BOUNDARY=' <<<"$status_output" | cut -d= -f2-)"
task_input_external_request_allowed="$(grep '^TASK_INPUT_EXTERNAL_REQUEST_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"
task_input_runtime_mutation_allowed="$(grep '^TASK_INPUT_RUNTIME_MUTATION_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"
real_credential_placeholder_boundary="$(grep '^REAL_CREDENTIAL_PLACEHOLDER_BOUNDARY=' <<<"$status_output" | cut -d= -f2-)"
real_credential_placeholder_policy="$(grep '^REAL_CREDENTIAL_PLACEHOLDER_POLICY=' <<<"$status_output" | cut -d= -f2-)"
placeholder_external_request_allowed="$(grep '^PLACEHOLDER_EXTERNAL_REQUEST_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"
placeholder_runtime_mutation_allowed="$(grep '^PLACEHOLDER_RUNTIME_MUTATION_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"

[[ "$real_handoff_adapter" == "present" ]] || fail "real handoff adapter should be present in review status output"
[[ "$real_handoff_mode" == "mock_only" ]] || fail "real handoff adapter should stay in mock_only mode"
[[ "$external_request_allowed" == "no" ]] || fail "real handoff adapter must not allow external requests"
[[ "$runtime_mutation_allowed" == "no" ]] || fail "real handoff adapter must not allow runtime mutation"
[[ "$real_handoff_task_input_contract" == "present" ]] || fail "real handoff task input contract should be present in review status output"
[[ "$real_handoff_task_input_boundary" == "review_only" ]] || fail "real handoff task input contract should stay review_only"
[[ "$task_input_external_request_allowed" == "no" ]] || fail "real handoff task input contract must not allow external requests"
[[ "$task_input_runtime_mutation_allowed" == "no" ]] || fail "real handoff task input contract must not allow runtime mutation"
[[ "$real_credential_placeholder_boundary" == "present" ]] || fail "real credential placeholder boundary should be present in review status output"
[[ "$real_credential_placeholder_policy" == "placeholder_only" ]] || fail "real credential placeholder policy should stay placeholder_only"
[[ "$placeholder_external_request_allowed" == "no" ]] || fail "placeholder boundary must not allow external requests"
[[ "$placeholder_runtime_mutation_allowed" == "no" ]] || fail "placeholder boundary must not allow runtime mutation"

case "$state" in
  synthetic_only)
    [[ "$domain_worth_buying" == "no" ]] || fail "domain worth buying should still be no for synthetic_only"
    [[ "$external_showcase_ready" == "no" ]] || fail "external showcase should still be no for synthetic_only"

    state_gate_output="$("$STATUS_SCRIPT" --require-state synthetic_only)"
    grep -q 'FIRST_CONTROLLED_SEND_STATE_GATE PASS: STATE=synthetic_only' <<<"$state_gate_output" || fail "state gate did not pass for synthetic_only"

    if domain_gate_output="$("$STATUS_SCRIPT" --check-domain-gate 2>&1)"; then
      fail "domain gate unexpectedly passed for synthetic_only"
    fi
    if ! grep -q 'FIRST_CONTROLLED_SEND_DOMAIN_GATE BLOCKED: DOMAIN_WORTH_BUYING=no' <<<"$domain_gate_output"; then
      fail "domain gate did not block with the expected message for synthetic_only"
    fi
    ;;
  ready_for_real_review)
    [[ "$domain_worth_buying" == "yes" ]] || fail "domain worth buying should be yes for ready_for_real_review"
    [[ "$external_showcase_ready" == "yes" ]] || fail "external showcase should be yes for ready_for_real_review"

    state_gate_output="$("$STATUS_SCRIPT" --require-state ready_for_real_review)"
    grep -q 'FIRST_CONTROLLED_SEND_STATE_GATE PASS: STATE=ready_for_real_review' <<<"$state_gate_output" || fail "state gate did not pass for ready_for_real_review"

    domain_gate_output="$("$STATUS_SCRIPT" --check-domain-gate 2>&1)" || fail "domain gate unexpectedly blocked for ready_for_real_review"
    grep -q 'FIRST_CONTROLLED_SEND_DOMAIN_GATE PASS: DOMAIN_WORTH_BUYING=yes' <<<"$domain_gate_output" || fail "domain gate did not pass with the expected message for ready_for_real_review"
    ;;
  *)
    fail "unsupported state from status report: ${state}"
    ;;
esac

echo "FIRST_CONTROLLED_SEND_STATUS_INTEGRATION PASS: ${state} stack consistent"

#!/usr/bin/env bash
# Verifies that the real handoff adapter evidence report rejects a drifted
# runtime fixture while preserving bounded review-only guarantees.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_adapter_runtime_fixture_drift.sh

Checks that the drift fixture:
- reports REAL_HANDOFF_MODE=drifted
- keeps external requests, runtime mutation, and live trading disabled
- blocks task opening with expected drift reasons

This script does not inject credentials, mutate runtime, issue external
requests, or authorize live trading.
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
  echo "REAL_HANDOFF_ADAPTER_RUNTIME_FIXTURE_DRIFT FAIL: cannot resolve repository root" >&2
  exit 1
}

REPORT_SCRIPT="${ROOT}/scripts/real_handoff_adapter_evidence_report.sh"

fail() {
  echo "REAL_HANDOFF_ADAPTER_RUNTIME_FIXTURE_DRIFT FAIL: $1" >&2
  exit 1
}

output="$("$REPORT_SCRIPT" --fixture drift)"

fixture="$(grep '^FIXTURE=' <<<"$output" | cut -d= -f2-)"
mode="$(grep '^REAL_HANDOFF_MODE=' <<<"$output" | cut -d= -f2-)"
external_request_allowed="$(grep '^EXTERNAL_REQUEST_ALLOWED=' <<<"$output" | cut -d= -f2-)"
runtime_mutation_allowed="$(grep '^RUNTIME_MUTATION_ALLOWED=' <<<"$output" | cut -d= -f2-)"
live_trading_allowed="$(grep '^LIVE_TRADING_ALLOWED=' <<<"$output" | cut -d= -f2-)"
task_opening_allowed="$(grep '^TASK_OPENING_ALLOWED=' <<<"$output" | cut -d= -f2-)"
blocked_reasons="$(grep '^BLOCKED_REASONS=' <<<"$output" | cut -d= -f2-)"

[[ "$fixture" == "drift" ]] || fail "fixture should be drift"
[[ "$mode" == "drifted" ]] || fail "drift fixture should report drifted mode"
[[ "$external_request_allowed" == "no" ]] || fail "drift fixture must keep external requests disabled"
[[ "$runtime_mutation_allowed" == "no" ]] || fail "drift fixture must keep runtime mutation disabled"
[[ "$live_trading_allowed" == "no" ]] || fail "drift fixture must keep live trading disabled"
[[ "$task_opening_allowed" == "no" ]] || fail "drift fixture must block task opening"
[[ "$blocked_reasons" == *"executor_mode_not_mock"* ]] || fail "missing executor_mode_not_mock drift reason"
[[ "$blocked_reasons" == *"real_enable_not_zero"* ]] || fail "missing real_enable_not_zero drift reason"

echo "REAL_HANDOFF_ADAPTER_RUNTIME_FIXTURE_DRIFT PASS: drift posture stays blocked"

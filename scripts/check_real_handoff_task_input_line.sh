#!/usr/bin/env bash
# Single-entry closeout check for the bounded real handoff task-input line.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_task_input_line.sh

Runs the bounded task-input line checks as one closeout gate:
- task input contract fixture matrix
- task input report/status alignment

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
  echo "REAL_HANDOFF_TASK_INPUT_LINE FAIL: cannot resolve repository root" >&2
  exit 1
}

if ! "${ROOT}/scripts/check_real_handoff_task_input_contract.sh"; then
  echo "REAL_HANDOFF_TASK_INPUT_LINE FAIL: task input contract check failed" >&2
  exit 1
fi

if ! "${ROOT}/scripts/check_real_handoff_task_input_report_integration.sh"; then
  echo "REAL_HANDOFF_TASK_INPUT_LINE FAIL: task input report integration check failed" >&2
  exit 1
fi

echo "REAL_HANDOFF_TASK_INPUT_LINE PASS: bounded task-input line closed out"

#!/usr/bin/env bash
# Single-entry closeout check for the bounded real handoff opening-prereq line.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_opening_prereq_line.sh

Runs the bounded real handoff opening-prereq line checks as one closeout gate:
- opening-prereq contract fixture matrix
- opening-prereq report/status alignment

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
  echo "REAL_HANDOFF_OPENING_PREREQ_LINE FAIL: cannot resolve repository root" >&2
  exit 1
}

if ! "${ROOT}/scripts/check_real_handoff_opening_prereq_contract.sh"; then
  echo "REAL_HANDOFF_OPENING_PREREQ_LINE FAIL: opening prereq contract check failed" >&2
  exit 1
fi

if ! bash "${ROOT}/scripts/check_real_handoff_opening_prereq_report_integration.sh"; then
  echo "REAL_HANDOFF_OPENING_PREREQ_LINE FAIL: opening prereq report integration check failed" >&2
  exit 1
fi

echo "REAL_HANDOFF_OPENING_PREREQ_LINE PASS: bounded opening-prereq line closed out"

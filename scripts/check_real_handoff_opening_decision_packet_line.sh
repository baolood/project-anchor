#!/usr/bin/env bash
# Single-entry closeout check for the bounded real handoff opening-decision-packet line.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_opening_decision_packet_line.sh

Runs the bounded real handoff opening-decision-packet line checks as one closeout gate:
- opening-decision-packet contract fixture matrix
- opening-decision-packet report/status alignment

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
  echo "REAL_HANDOFF_OPENING_DECISION_PACKET_LINE FAIL: cannot resolve repository root" >&2
  exit 1
}

if ! "${ROOT}/scripts/check_real_handoff_opening_decision_packet_contract.sh"; then
  echo "REAL_HANDOFF_OPENING_DECISION_PACKET_LINE FAIL: opening decision packet contract check failed" >&2
  exit 1
fi

if ! bash "${ROOT}/scripts/check_real_handoff_opening_decision_packet_report_integration.sh"; then
  echo "REAL_HANDOFF_OPENING_DECISION_PACKET_LINE FAIL: opening decision packet report integration check failed" >&2
  exit 1
fi

echo "REAL_HANDOFF_OPENING_DECISION_PACKET_LINE PASS: bounded opening-decision-packet line closed out"

#!/usr/bin/env bash
# Single-entry closeout check for the bounded real handoff opening-bundle line.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_opening_bundle_line.sh

Runs the bounded real handoff opening-bundle line checks as one closeout gate:
- opening-bundle contract fixture matrix
- opening-bundle report/status alignment

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
  echo "REAL_HANDOFF_OPENING_BUNDLE_LINE FAIL: cannot resolve repository root" >&2
  exit 1
}

if ! "${ROOT}/scripts/check_real_handoff_opening_bundle_contract.sh"; then
  echo "REAL_HANDOFF_OPENING_BUNDLE_LINE FAIL: opening bundle contract check failed" >&2
  exit 1
fi

if ! bash "${ROOT}/scripts/check_real_handoff_opening_bundle_report_integration.sh"; then
  echo "REAL_HANDOFF_OPENING_BUNDLE_LINE FAIL: opening bundle report integration check failed" >&2
  exit 1
fi

echo "REAL_HANDOFF_OPENING_BUNDLE_LINE PASS: bounded opening-bundle line closed out"

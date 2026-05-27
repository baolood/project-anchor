#!/usr/bin/env bash
# Single-entry closeout check for the bounded real handoff explicit-runtime-send line.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_explicit_runtime_send_line.sh

Runs the bounded explicit-runtime-send line checks as one closeout gate:
- explicit-runtime-send boundary fixture matrix
- explicit-runtime-send report/status alignment

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
  echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_LINE FAIL: cannot resolve repository root" >&2
  exit 1
}

if ! "${ROOT}/scripts/check_real_handoff_explicit_runtime_send_boundary.sh"; then
  echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_LINE FAIL: explicit runtime send boundary check failed" >&2
  exit 1
fi

if ! bash "${ROOT}/scripts/check_real_handoff_explicit_runtime_send_report_integration.sh"; then
  echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_LINE FAIL: explicit runtime send report integration check failed" >&2
  exit 1
fi

echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_LINE PASS: bounded explicit-runtime-send line closed out"

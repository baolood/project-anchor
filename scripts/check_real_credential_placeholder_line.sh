#!/usr/bin/env bash
# Single-entry closeout check for the bounded real credential placeholder line.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_credential_placeholder_line.sh

Runs the bounded real credential placeholder line checks as one closeout gate:
- placeholder boundary fixture matrix
- placeholder report/status alignment

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
  echo "REAL_CREDENTIAL_PLACEHOLDER_LINE FAIL: cannot resolve repository root" >&2
  exit 1
}

if ! "${ROOT}/scripts/check_real_credential_placeholder_boundary.sh"; then
  echo "REAL_CREDENTIAL_PLACEHOLDER_LINE FAIL: placeholder boundary check failed" >&2
  exit 1
fi

if ! "${ROOT}/scripts/check_real_credential_placeholder_report_integration.sh"; then
  echo "REAL_CREDENTIAL_PLACEHOLDER_LINE FAIL: placeholder report integration check failed" >&2
  exit 1
fi

echo "REAL_CREDENTIAL_PLACEHOLDER_LINE PASS: bounded placeholder line closed out"

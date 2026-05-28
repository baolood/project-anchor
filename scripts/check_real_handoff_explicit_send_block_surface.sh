#!/usr/bin/env bash
# Groups the explicit-send hard-block surface without changing the underlying
# narrow-check ownership or runtime posture.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_explicit_send_block_surface.sh

Runs the current hard explicit-send blockers as one grouped ownership surface:
- testnet credential runtime presence boundary
- testnet external request dry approval boundary
- explicit send approval packet boundary
- explicit runtime send line

This wrapper preserves fail-closed behavior by calling the existing narrow
checks directly. It does not inject credentials, mutate runtime, issue
external requests, or authorize live trading.
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
  echo "REAL_HANDOFF_EXPLICIT_SEND_BLOCK_SURFACE FAIL: cannot resolve repository root" >&2
  exit 1
}

if ! "${ROOT}/scripts/check_real_handoff_testnet_credential_runtime_presence_boundary.sh"; then
  echo "REAL_HANDOFF_EXPLICIT_SEND_BLOCK_SURFACE FAIL: testnet credential runtime presence boundary check failed" >&2
  exit 1
fi

if ! "${ROOT}/scripts/check_real_handoff_testnet_external_request_dry_approval_boundary.sh"; then
  echo "REAL_HANDOFF_EXPLICIT_SEND_BLOCK_SURFACE FAIL: testnet external request dry approval boundary check failed" >&2
  exit 1
fi

if ! "${ROOT}/scripts/check_real_handoff_explicit_send_approval_packet_boundary.sh"; then
  echo "REAL_HANDOFF_EXPLICIT_SEND_BLOCK_SURFACE FAIL: explicit send approval packet boundary check failed" >&2
  exit 1
fi

if ! "${ROOT}/scripts/check_real_handoff_explicit_runtime_send_line.sh"; then
  echo "REAL_HANDOFF_EXPLICIT_SEND_BLOCK_SURFACE FAIL: explicit runtime send line check failed" >&2
  exit 1
fi

echo "REAL_HANDOFF_EXPLICIT_SEND_BLOCK_SURFACE PASS: grouped explicit-send hard blockers preserved"

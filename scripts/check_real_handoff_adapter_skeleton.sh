#!/usr/bin/env bash
# Verifies the real handoff adapter skeleton keeps its bounded mock-posture
# contract without requiring real credentials or external requests.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_adapter_skeleton.sh

Checks that the real handoff adapter skeleton:
- accepts a canonical mock-posture fixture
- rejects a drifted real-mode fixture
- stays review-safe and credential-value-free

This script does not inject credentials, mutate runtime, issue external
requests, or approve live trading.
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
  echo "REAL_HANDOFF_ADAPTER_SKELETON_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

cd "${ROOT}/anchor-backend"

python3 - <<'PY'
from app.executors.testnet_real_handoff_adapter import (
    build_real_handoff_adapter_skeleton,
    build_real_handoff_runtime_snapshot,
)


def fail(msg: str) -> None:
    raise SystemExit(f"REAL_HANDOFF_ADAPTER_SKELETON_CHECK FAIL: {msg}")


fixture = {
    "TESTNET_EXCHANGE_BASE_URL": "https://testnet.binancefuture.com",
    "TESTNET_EXECUTOR_MODE": "mock",
    "TESTNET_EXECUTOR_REAL_ENABLE": "0",
    "TESTNET_EXCHANGE_API_KEY": "",
    "TESTNET_EXCHANGE_API_SECRET": "",
    "TESTNET_EXCHANGE_KEY_ID": "",
}

snapshot = build_real_handoff_runtime_snapshot(fixture)
if snapshot["configured_origin"] != "https://testnet.binancefuture.com":
    fail("configured origin fixture mismatch")
if not snapshot["credential_free_mock_posture"]:
    fail("fixture should remain credential-free mock posture")
if snapshot["blocked_reasons"] != []:
    fail("fixture should not accumulate blocked reasons")

drift = build_real_handoff_adapter_skeleton(
    {
        "TESTNET_EXCHANGE_BASE_URL": "https://testnet.binancefuture.com",
        "TESTNET_EXECUTOR_MODE": "real",
        "TESTNET_EXECUTOR_REAL_ENABLE": "1",
    }
)
if drift["task_opening_allowed"]:
    fail("drifted real-mode fixture should not be openable")
if "executor_mode_not_mock" not in drift["current_runtime"]["blocked_reasons"]:
    fail("missing executor-mode drift reason")
if "real_enable_not_zero" not in drift["current_runtime"]["blocked_reasons"]:
    fail("missing real-enable drift reason")

print("REAL_HANDOFF_ADAPTER_SKELETON_CHECK PASS: bounded adapter contract intact")
PY

#!/usr/bin/env bash
# Verifies the mocked external executor V1 line stays offline, reviewable, and
# explicitly gated away from unintended real-wire execution.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_external_executor_mocked_v1.sh

Checks the repository structure for the Real Testnet External Executor Mocked
V1 slice.

This check verifies:
- runner owns the canonical ORDER + execution_mode=testnet mocked executor line
- mocked executor emits REQUESTED / ACCEPTED / REJECTED semantics
- real wire stays explicitly gated behind TESTNET_EXECUTOR_REAL_ENABLE
- focused tests cover mocked success/failure chains and real-wire gating cases

This script does not execute any external request, require real credentials, or
authorize live trading.
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
  echo "REAL_TESTNET_EXTERNAL_EXECUTOR_MOCKED_V1_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

RUNNER="${ROOT}/anchor-backend/app/actions/runner.py"
REAL_EXECUTOR="${ROOT}/anchor-backend/app/executors/testnet_order_executor.py"
TEST_FILE="${ROOT}/anchor-backend/tests/test_testnet_external_executor_v1.py"

for required in "$RUNNER" "$REAL_EXECUTOR" "$TEST_FILE"; do
  [[ -f "$required" ]] || {
    echo "REAL_TESTNET_EXTERNAL_EXECUTOR_MOCKED_V1_CHECK FAIL: missing required file $required" >&2
    exit 1
  }
done

python3 - <<'PY' "$RUNNER" "$REAL_EXECUTOR" "$TEST_FILE"
from pathlib import Path
import sys
from typing import List

runner_path = Path(sys.argv[1])
real_executor_path = Path(sys.argv[2])
test_path = Path(sys.argv[3])

runner = runner_path.read_text()
real_executor = real_executor_path.read_text()
tests = test_path.read_text()


def require(text: str, needle: str, label: str, missing: List[str]) -> None:
    if needle not in text:
        missing.append(label)


missing: List[str] = []

require(runner, 'executor_mode == "mock"', "runner_mock_mode_branch", missing)
require(runner, 'executor_mode == "real"', "runner_real_mode_branch", missing)
require(runner, 'TESTNET_EXECUTOR_REQUESTED', "runner_requested_event", missing)
require(runner, 'TESTNET_EXECUTOR_ACCEPTED', "runner_accepted_event", missing)
require(runner, 'TESTNET_EXECUTOR_REJECTED', "runner_rejected_event", missing)
require(runner, 'TESTNET_EXECUTOR_MODE_INVALID', "runner_invalid_mode_guard", missing)
require(runner, 'TESTNET_EXECUTOR_NOT_IMPLEMENTED', "runner_not_implemented_guard", missing)
require(runner, 'TESTNET_EXECUTOR_MOCK_OUTCOME', "runner_mock_outcome_env", missing)
require(runner, 'timeout_policy_label": "single_attempt_v1"', "runner_single_attempt_policy", missing)

require(real_executor, 'TESTNET_EXECUTOR_REAL_ENABLE', "real_executor_explicit_enable_flag", missing)
require(real_executor, 'TESTNET_REAL_WIRE_DISABLED', "real_executor_disabled_guard", missing)
require(real_executor, 'TESTNET_EXECUTOR_TIMEOUT', "real_executor_timeout_family", missing)
require(real_executor, 'TESTNET_EXECUTOR_NETWORK_ERROR', "real_executor_network_family", missing)
require(real_executor, 'TESTNET_EXECUTOR_ACCEPTED', "real_executor_accepted_terminal", missing)
require(real_executor, 'TESTNET_EXECUTOR_REJECTED', "real_executor_rejected_terminal", missing)

for test_name in (
    "test_runner_emits_mocked_success_external_chain",
    "test_runner_emits_mocked_auth_failed_external_chain",
    "test_runner_emits_mocked_timeout_external_chain",
    "test_runner_emits_mocked_validation_failed_external_chain",
    "test_runner_emits_mocked_network_error_external_chain",
    "test_runner_maps_unknown_mock_outcome_to_unexpected_family",
    "test_runner_real_mode_stays_disabled_without_explicit_enable_flag",
    "test_runner_invalid_executor_mode_does_not_silently_go_real",
):
    require(tests, f"def {test_name}(", f"test_coverage:{test_name}", missing)

if missing:
    raise SystemExit(
        "REAL_TESTNET_EXTERNAL_EXECUTOR_MOCKED_V1_CHECK FAIL: missing required mocked-executor guardrails: "
        + ",".join(missing)
    )

print("MOCKED_EXTERNAL_EXECUTOR_V1=PASS")
print("CANONICAL_PATH=ORDER:testnet")
print("MOCK_EXECUTOR_PATH=present")
print("REAL_WIRE_GATED=yes")
print("EXTERNAL_REQUEST_ATTEMPTED=no")
print("LIVE_TRADING=false")
print(
    "REAL_TESTNET_EXTERNAL_EXECUTOR_MOCKED_V1_CHECK PASS: mocked external executor line remains offline, gated, and reviewable"
)
PY

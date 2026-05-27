#!/usr/bin/env bash
# Runs the agreed local backend/testnet/executor smoke tests using the known
# working Python environment.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_backend_testnet_executor_smoke.sh [--test FILE_PATTERN]

Runs backend unittest smoke coverage for testnet/executor work with:

  PYTHONPATH=anchor-backend /opt/anaconda3/bin/python -m unittest discover ...

Default smoke set:
- test_testnet_external_executor_v1.py
- test_testnet_boundary_preflight_v1.py
- test_testnet_real_wire_v1.py

Options:
  --test FILE_PATTERN   Run only one unittest file pattern from anchor-backend/tests
  -h, --help            Show this help
EOF
}

PYTHON_BIN="/opt/anaconda3/bin/python"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="${ROOT}/anchor-backend/tests"

declare -a TEST_PATTERNS=(
  "test_testnet_external_executor_v1.py"
  "test_testnet_boundary_preflight_v1.py"
  "test_testnet_real_wire_v1.py"
)

while (($# > 0)); do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --test)
      shift
      if (($# == 0)); then
        echo "BACKEND_TESTNET_EXECUTOR_SMOKE FAIL: --test requires a file pattern" >&2
        exit 2
      fi
      TEST_PATTERNS=("$1")
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
  shift
done

[[ -x "${PYTHON_BIN}" ]] || {
  echo "BACKEND_TESTNET_EXECUTOR_SMOKE FAIL: python not executable at ${PYTHON_BIN}" >&2
  exit 1
}

[[ -d "${TEST_DIR}" ]] || {
  echo "BACKEND_TESTNET_EXECUTOR_SMOKE FAIL: missing test directory ${TEST_DIR}" >&2
  exit 1
}

PYTHON_VERSION="$("${PYTHON_BIN}" --version 2>&1)"
echo "BACKEND_TESTNET_EXECUTOR_SMOKE_PYTHON=${PYTHON_BIN}"
echo "BACKEND_TESTNET_EXECUTOR_SMOKE_VERSION=${PYTHON_VERSION}"

for pattern in "${TEST_PATTERNS[@]}"; do
  echo "BACKEND_TESTNET_EXECUTOR_SMOKE_RUN=${pattern}"
  (
    cd "${ROOT}"
    PYTHONPATH=anchor-backend "${PYTHON_BIN}" -m unittest discover \
      -s anchor-backend/tests \
      -p "${pattern}"
  )
done

echo "BACKEND_TESTNET_EXECUTOR_SMOKE PASS: ${TEST_PATTERNS[*]}"

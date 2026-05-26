#!/usr/bin/env bash
# Emits a machine-readable evidence snapshot for the bounded real handoff
# adapter slice using the canonical mock fixture.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "REAL_HANDOFF_ADAPTER_EVIDENCE FAIL: cannot resolve repository root" >&2
  exit 1
}

OUT_FILE="${OUT_FILE:-}"
FIXTURE="mock"

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "REAL_HANDOFF_ADAPTER_EVIDENCE FAIL: ${opt} requires a value." >&2
    exit 2
  fi
}

while (($# > 0)); do
  case "$1" in
    --fixture)
      require_value "--fixture" "${2:-}"
      FIXTURE="${2:-}"
      case "$FIXTURE" in
        mock|drift) ;;
        *)
          echo "REAL_HANDOFF_ADAPTER_EVIDENCE FAIL: unsupported fixture: ${FIXTURE}" >&2
          exit 2
          ;;
      esac
      shift 2
      ;;
    --out)
      require_value "--out" "${2:-}"
      OUT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/real_handoff_adapter_evidence_report.sh [--fixture <mock|drift>] [--out <path>]

Options:
  --fixture <mock|drift>  Emit evidence for the bounded mock fixture or a
                          drifted real-mode fixture.
  --out <path>            Write the report to a file (stdout always prints).

Fields:
  REAL_HANDOFF_ADAPTER
  FIXTURE
  REAL_HANDOFF_MODE
  EXTERNAL_REQUEST_ALLOWED
  RUNTIME_MUTATION_ALLOWED
  LIVE_TRADING_ALLOWED
  TASK_OPENING_ALLOWED
  CREDENTIAL_FREE_MOCK_POSTURE
  CONFIGURED_ORIGIN
  BLOCKED_REASONS
  FUTURE_HANDOFF_KEYS

This report uses bounded local fixtures only. It does not inject
credentials, mutate runtime, issue external requests, or authorize live
trading.
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Run with --help for usage." >&2
      exit 2
      ;;
  esac
done

report="$(
  cd "${ROOT}/anchor-backend"
  FIXTURE="${FIXTURE}" python3 - <<'PY'
import os

from app.executors.testnet_real_handoff_adapter import build_real_handoff_adapter_skeleton

fixture_name = os.environ["FIXTURE"]
fixture = {
    "TESTNET_EXCHANGE_BASE_URL": "https://testnet.binancefuture.com",
    "TESTNET_EXECUTOR_MODE": "mock",
    "TESTNET_EXECUTOR_REAL_ENABLE": "0",
    "TESTNET_EXCHANGE_API_KEY": "",
    "TESTNET_EXCHANGE_API_SECRET": "",
    "TESTNET_EXCHANGE_KEY_ID": "",
}

if fixture_name == "drift":
    fixture["TESTNET_EXECUTOR_MODE"] = "real"
    fixture["TESTNET_EXECUTOR_REAL_ENABLE"] = "1"

adapter = build_real_handoff_adapter_skeleton(fixture)

runtime = adapter["current_runtime"]
mode = "mock_only" if runtime["credential_free_mock_posture"] else "drifted"
blocked_reasons = ",".join(runtime["blocked_reasons"]) or "none"
future_keys = ",".join(adapter["future_handoff_keys"])

print("REAL_HANDOFF_ADAPTER_EVIDENCE")
print("REAL_HANDOFF_ADAPTER=present")
print(f"FIXTURE={fixture_name}")
print(f"REAL_HANDOFF_MODE={mode}")
print(
    "EXTERNAL_REQUEST_ALLOWED="
    + ("yes" if adapter["allows_external_request"] else "no")
)
print(
    "RUNTIME_MUTATION_ALLOWED="
    + ("yes" if adapter["allows_runtime_mutation"] else "no")
)
print(
    "LIVE_TRADING_ALLOWED="
    + ("yes" if adapter["allows_live_trading"] else "no")
)
print(
    "TASK_OPENING_ALLOWED="
    + ("yes" if adapter["task_opening_allowed"] else "no")
)
print(
    "CREDENTIAL_FREE_MOCK_POSTURE="
    + ("yes" if runtime["credential_free_mock_posture"] else "no")
)
print(f"CONFIGURED_ORIGIN={runtime['configured_origin']}")
print(f"BLOCKED_REASONS={blocked_reasons}")
print(f"FUTURE_HANDOFF_KEYS={future_keys}")
PY
)"

echo "$report"

if [[ -n "$OUT_FILE" ]]; then
  if [[ "${OUT_FILE}" == */ ]]; then
    echo "REAL_HANDOFF_ADAPTER_EVIDENCE FAIL: --out expects a file path, got directory-like path: ${OUT_FILE}" >&2
    exit 2
  fi
  if [[ -d "${OUT_FILE}" ]]; then
    echo "REAL_HANDOFF_ADAPTER_EVIDENCE FAIL: --out expects a file path, got directory: ${OUT_FILE}" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%s\n' "$report" > "$OUT_FILE"
  echo "WROTE_REPORT=$OUT_FILE"
fi

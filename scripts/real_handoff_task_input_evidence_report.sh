#!/usr/bin/env bash
# Emits a machine-readable evidence snapshot for the bounded real handoff task
# input contract using a review-only fixture.
set -euo pipefail

OUT_FILE="${OUT_FILE:-}"

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "REAL_HANDOFF_TASK_INPUT_EVIDENCE FAIL: ${opt} requires a value." >&2
    exit 2
  fi
}

while (($# > 0)); do
  case "$1" in
    --out)
      require_value "--out" "${2:-}"
      OUT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/real_handoff_task_input_evidence_report.sh [--out <path>]

Fields:
  REAL_HANDOFF_TASK_INPUT_EVIDENCE
  REAL_HANDOFF_TASK_INPUT_CONTRACT
  REAL_HANDOFF_TASK_INPUT_BOUNDARY
  TASK_INPUT_EXTERNAL_REQUEST_ALLOWED
  TASK_INPUT_RUNTIME_MUTATION_ALLOWED
  TASK_INPUT_LIVE_TRADING_ALLOWED
  TASK_INPUT_EXPECTED_EXECUTOR_MODE
  TASK_INPUT_EXPECTED_REAL_ENABLE
  TASK_INPUT_EVIDENCE_COMMAND_ID
  TASK_INPUT_CREDENTIAL_SLOT_COUNT
  TASK_INPUT_CREDENTIAL_SLOTS

This report uses a bounded review-only fixture. It does not inject
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
  python3 - <<'PY'
payload = {
    "handoff_id": "real-handoff-20260526-001",
    "requested_by": "baolood",
    "reviewed_state": "ready_for_real_review",
    "evidence_command_id": "order-mocksmoke-20260525111528",
    "artifact_path": "docs/reviews/real_testnet/FIRST_CONTROLLED_SEND_2026-05-25_order-mocksmoke-20260525111528.md",
    "host_label": "binance_futures_testnet",
    "configured_origin": "https://testnet.binancefuture.com",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "credential_slots_requested": [
        "TESTNET_EXCHANGE_API_KEY",
        "TESTNET_EXCHANGE_API_SECRET",
        "TESTNET_EXCHANGE_KEY_ID",
    ],
    "ticket_ref": "RH-001",
    "notes": "bounded handoff planning input",
}

slots = payload["credential_slots_requested"]

print("REAL_HANDOFF_TASK_INPUT_EVIDENCE")
print("REAL_HANDOFF_TASK_INPUT_CONTRACT=present")
print("REAL_HANDOFF_TASK_INPUT_BOUNDARY=review_only")
print("TASK_INPUT_EXTERNAL_REQUEST_ALLOWED=no")
print("TASK_INPUT_RUNTIME_MUTATION_ALLOWED=no")
print("TASK_INPUT_LIVE_TRADING_ALLOWED=no")
print(f"TASK_INPUT_EXPECTED_EXECUTOR_MODE={payload['expected_executor_mode']}")
print(f"TASK_INPUT_EXPECTED_REAL_ENABLE={payload['expected_real_enable']}")
print(f"TASK_INPUT_EVIDENCE_COMMAND_ID={payload['evidence_command_id']}")
print(f"TASK_INPUT_CREDENTIAL_SLOT_COUNT={len(slots)}")
print("TASK_INPUT_CREDENTIAL_SLOTS=" + ",".join(slots))
PY
)"

echo "$report"

if [[ -n "$OUT_FILE" ]]; then
  if [[ "${OUT_FILE}" == */ ]]; then
    echo "REAL_HANDOFF_TASK_INPUT_EVIDENCE FAIL: --out expects a file path, got directory-like path: ${OUT_FILE}" >&2
    exit 2
  fi
  if [[ -d "${OUT_FILE}" ]]; then
    echo "REAL_HANDOFF_TASK_INPUT_EVIDENCE FAIL: --out expects a file path, got directory: ${OUT_FILE}" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%s\n' "$report" > "$OUT_FILE"
  echo "WROTE_REPORT=$OUT_FILE"
fi

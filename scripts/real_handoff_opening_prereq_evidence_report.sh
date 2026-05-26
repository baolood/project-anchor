#!/usr/bin/env bash
# Emits a machine-readable evidence snapshot for the bounded real handoff
# opening-prereq contract using a review-only fixture.
set -euo pipefail

OUT_FILE="${OUT_FILE:-}"

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "REAL_HANDOFF_OPENING_PREREQ_EVIDENCE FAIL: ${opt} requires a value." >&2
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
Usage: ./scripts/real_handoff_opening_prereq_evidence_report.sh [--out <path>]

Fields:
  REAL_HANDOFF_OPENING_PREREQ_EVIDENCE
  REAL_HANDOFF_OPENING_PREREQ_CONTRACT
  REAL_HANDOFF_OPENING_PREREQ_BOUNDARY
  OPENING_PREREQ_EXTERNAL_REQUEST_ALLOWED
  OPENING_PREREQ_RUNTIME_MUTATION_ALLOWED
  OPENING_PREREQ_LIVE_TRADING_ALLOWED
  OPENING_PREREQ_REVIEWED_STATE
  OPENING_PREREQ_ADAPTER_LINE_STATUS
  OPENING_PREREQ_TASK_INPUT_LINE_STATUS
  OPENING_PREREQ_PLACEHOLDER_LINE_STATUS
  OPENING_PREREQ_EXPECTED_EXECUTOR_MODE
  OPENING_PREREQ_EXPECTED_REAL_ENABLE
  OPENING_PREREQ_CREDENTIAL_SLOT_COUNT
  OPENING_PREREQ_CREDENTIAL_SLOTS

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
    "opening_id": "real-handoff-opening-20260526-001",
    "reviewed_state": "ready_for_real_review",
    "evidence_command_id": "order-mocksmoke-20260525111528",
    "artifact_path": "docs/reviews/real_testnet/FIRST_CONTROLLED_SEND_2026-05-25_order-mocksmoke-20260525111528.md",
    "adapter_line_status": "green",
    "task_input_line_status": "green",
    "placeholder_line_status": "green",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "credential_slots_requested": [
        "TESTNET_EXCHANGE_API_KEY",
        "TESTNET_EXCHANGE_API_SECRET",
        "TESTNET_EXCHANGE_KEY_ID",
    ],
    "ticket_ref": "RHO-001",
    "notes": "bounded opening prereq contract",
}

boundary = "review_only"
if payload["expected_executor_mode"] != "mock" or payload["expected_real_enable"] != "0":
    boundary = "invalid"
if (
    payload["reviewed_state"] != "ready_for_real_review"
    or payload["adapter_line_status"] != "green"
    or payload["task_input_line_status"] != "green"
    or payload["placeholder_line_status"] != "green"
):
    boundary = "invalid"

slots = payload["credential_slots_requested"]

print("REAL_HANDOFF_OPENING_PREREQ_EVIDENCE")
print("REAL_HANDOFF_OPENING_PREREQ_CONTRACT=present")
print(f"REAL_HANDOFF_OPENING_PREREQ_BOUNDARY={boundary}")
print("OPENING_PREREQ_EXTERNAL_REQUEST_ALLOWED=no")
print("OPENING_PREREQ_RUNTIME_MUTATION_ALLOWED=no")
print("OPENING_PREREQ_LIVE_TRADING_ALLOWED=no")
print(f"OPENING_PREREQ_REVIEWED_STATE={payload['reviewed_state']}")
print(f"OPENING_PREREQ_ADAPTER_LINE_STATUS={payload['adapter_line_status']}")
print(f"OPENING_PREREQ_TASK_INPUT_LINE_STATUS={payload['task_input_line_status']}")
print(f"OPENING_PREREQ_PLACEHOLDER_LINE_STATUS={payload['placeholder_line_status']}")
print(f"OPENING_PREREQ_EXPECTED_EXECUTOR_MODE={payload['expected_executor_mode']}")
print(f"OPENING_PREREQ_EXPECTED_REAL_ENABLE={payload['expected_real_enable']}")
print(f"OPENING_PREREQ_CREDENTIAL_SLOT_COUNT={len(slots)}")
print("OPENING_PREREQ_CREDENTIAL_SLOTS=" + ",".join(slots))
PY
)"

echo "$report"

if [[ -n "$OUT_FILE" ]]; then
  if [[ "${OUT_FILE}" == */ ]]; then
    echo "REAL_HANDOFF_OPENING_PREREQ_EVIDENCE FAIL: --out expects a file path, got directory-like path: ${OUT_FILE}" >&2
    exit 2
  fi
  if [[ -d "${OUT_FILE}" ]]; then
    echo "REAL_HANDOFF_OPENING_PREREQ_EVIDENCE FAIL: --out expects a file path, got directory: ${OUT_FILE}" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%s\n' "$report" > "$OUT_FILE"
  echo "WROTE_REPORT=$OUT_FILE"
fi

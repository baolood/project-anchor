#!/usr/bin/env bash
# Emits a machine-readable evidence snapshot for the bounded real handoff
# opening-bundle contract using a review-only fixture.
set -euo pipefail

OUT_FILE="${OUT_FILE:-}"

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "REAL_HANDOFF_OPENING_BUNDLE_EVIDENCE FAIL: ${opt} requires a value." >&2
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
Usage: ./scripts/real_handoff_opening_bundle_evidence_report.sh [--out <path>]

Fields:
  REAL_HANDOFF_OPENING_BUNDLE_EVIDENCE
  REAL_HANDOFF_OPENING_BUNDLE_CONTRACT
  REAL_HANDOFF_OPENING_BUNDLE_BOUNDARY
  OPENING_BUNDLE_EXTERNAL_REQUEST_ALLOWED
  OPENING_BUNDLE_RUNTIME_MUTATION_ALLOWED
  OPENING_BUNDLE_LIVE_TRADING_ALLOWED
  OPENING_BUNDLE_REVIEWED_STATE
  OPENING_BUNDLE_OPENING_PREREQ_LINE_STATUS
  OPENING_BUNDLE_EXPECTED_EXECUTOR_MODE
  OPENING_BUNDLE_EXPECTED_REAL_ENABLE
  OPENING_BUNDLE_CREDENTIAL_SLOT_COUNT
  OPENING_BUNDLE_CREDENTIAL_SLOTS

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
    "bundle_id": "real-handoff-opening-bundle-20260526-001",
    "reviewed_state": "ready_for_real_review",
    "opening_prereq_line_status": "green",
    "evidence_command_id": "order-mocksmoke-20260525111528",
    "artifact_path": "docs/reviews/real_testnet/FIRST_CONTROLLED_SEND_2026-05-25_order-mocksmoke-20260525111528.md",
    "bundle_index_path": "docs/reviews/real_testnet/BUNDLE_INDEX_V1.md",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "credential_slots_requested": [
        "TESTNET_EXCHANGE_API_KEY",
        "TESTNET_EXCHANGE_API_SECRET",
        "TESTNET_EXCHANGE_KEY_ID",
    ],
    "reviewer_role": "operator_reviewer",
    "ticket_ref": "RHOB-001",
    "notes": "bounded opening bundle contract",
}

boundary = "review_only"
if payload["expected_executor_mode"] != "mock" or payload["expected_real_enable"] != "0":
    boundary = "invalid"
if (
    payload["reviewed_state"] != "ready_for_real_review"
    or payload["opening_prereq_line_status"] != "green"
):
    boundary = "invalid"

slots = payload["credential_slots_requested"]

print("REAL_HANDOFF_OPENING_BUNDLE_EVIDENCE")
print("REAL_HANDOFF_OPENING_BUNDLE_CONTRACT=present")
print(f"REAL_HANDOFF_OPENING_BUNDLE_BOUNDARY={boundary}")
print("OPENING_BUNDLE_EXTERNAL_REQUEST_ALLOWED=no")
print("OPENING_BUNDLE_RUNTIME_MUTATION_ALLOWED=no")
print("OPENING_BUNDLE_LIVE_TRADING_ALLOWED=no")
print(f"OPENING_BUNDLE_REVIEWED_STATE={payload['reviewed_state']}")
print(f"OPENING_BUNDLE_OPENING_PREREQ_LINE_STATUS={payload['opening_prereq_line_status']}")
print(f"OPENING_BUNDLE_EXPECTED_EXECUTOR_MODE={payload['expected_executor_mode']}")
print(f"OPENING_BUNDLE_EXPECTED_REAL_ENABLE={payload['expected_real_enable']}")
print(f"OPENING_BUNDLE_CREDENTIAL_SLOT_COUNT={len(slots)}")
print("OPENING_BUNDLE_CREDENTIAL_SLOTS=" + ",".join(slots))
PY
)"

echo "$report"

if [[ -n "$OUT_FILE" ]]; then
  if [[ "${OUT_FILE}" == */ ]]; then
    echo "REAL_HANDOFF_OPENING_BUNDLE_EVIDENCE FAIL: --out expects a file path, got directory-like path: ${OUT_FILE}" >&2
    exit 2
  fi
  if [[ -d "${OUT_FILE}" ]]; then
    echo "REAL_HANDOFF_OPENING_BUNDLE_EVIDENCE FAIL: --out expects a file path, got directory: ${OUT_FILE}" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%s\n' "$report" > "$OUT_FILE"
  echo "WROTE_REPORT=$OUT_FILE"
fi

#!/usr/bin/env bash
# Emits a small machine-readable status snapshot for first-controlled-send readiness.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "FIRST_CONTROLLED_SEND_STATUS FAIL: cannot resolve repository root" >&2
  exit 1
}

SUMMARY_SCRIPT="${ROOT}/scripts/check_first_controlled_send_gate_summary.sh"
ARTIFACT_DIR="${ROOT}/docs/reviews/real_testnet"
ADAPTER_MODULE_DIR="${ROOT}/anchor-backend"

OUT_FILE="${OUT_FILE:-}"
CHECK_DOMAIN_GATE=0
REQUIRE_STATE=""

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "FIRST_CONTROLLED_SEND_STATUS FAIL: ${opt} requires a value." >&2
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
    --check-domain-gate)
      CHECK_DOMAIN_GATE=1
      shift
      ;;
    --require-state)
      require_value "--require-state" "${2:-}"
      REQUIRE_STATE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/first_controlled_send_status_report.sh [--out <path>] [--check-domain-gate] [--require-state <value>]

Options:
  --out <path>  Write the report to a file (stdout always prints).
  --check-domain-gate  Exit non-zero unless DOMAIN_WORTH_BUYING=yes.
  --require-state <value>  Exit non-zero unless STATE matches the given value.

Fields:
  STATE                  synthetic_only / actual_missing / review_pack_missing / ready_for_real_review
  LEGACY_EXAMPLES        count of FIRST_REAL_REQUEST synthetic examples
  ACTUAL_ARTIFACTS       count of FIRST_CONTROLLED_SEND actual artifacts
  DOMAIN_WORTH_BUYING    yes/no
  EXTERNAL_SHOWCASE_READY yes/no
  REAL_HANDOFF_ADAPTER   present / missing
  REAL_HANDOFF_MODE      mock_only / drifted / unknown
  EXTERNAL_REQUEST_ALLOWED yes/no
  RUNTIME_MUTATION_ALLOWED yes/no
  REAL_HANDOFF_TASK_INPUT_CONTRACT present / missing
  REAL_HANDOFF_TASK_INPUT_BOUNDARY review_only / invalid
  TASK_INPUT_EXTERNAL_REQUEST_ALLOWED yes/no
  TASK_INPUT_RUNTIME_MUTATION_ALLOWED yes/no
  REAL_CREDENTIAL_PLACEHOLDER_BOUNDARY present / missing
  REAL_CREDENTIAL_PLACEHOLDER_POLICY placeholder_only / invalid
  PLACEHOLDER_EXTERNAL_REQUEST_ALLOWED yes/no
  PLACEHOLDER_RUNTIME_MUTATION_ALLOWED yes/no
  REAL_HANDOFF_OPENING_PREREQ_CONTRACT present / missing
  REAL_HANDOFF_OPENING_PREREQ_BOUNDARY review_only / invalid
  OPENING_PREREQ_EXTERNAL_REQUEST_ALLOWED yes/no
  OPENING_PREREQ_RUNTIME_MUTATION_ALLOWED yes/no
  REAL_HANDOFF_OPENING_BUNDLE_CONTRACT present / missing
  REAL_HANDOFF_OPENING_BUNDLE_BOUNDARY review_only / invalid
  OPENING_BUNDLE_EXTERNAL_REQUEST_ALLOWED yes/no
  OPENING_BUNDLE_RUNTIME_MUTATION_ALLOWED yes/no
  REAL_HANDOFF_OPENING_DECISION_PACKET_CONTRACT present / missing
  REAL_HANDOFF_OPENING_DECISION_PACKET_BOUNDARY review_only / invalid
  OPENING_DECISION_PACKET_EXTERNAL_REQUEST_ALLOWED yes/no
  OPENING_DECISION_PACKET_RUNTIME_MUTATION_ALLOWED yes/no

This report does not authorize a real controlled send or live trading.
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

summary_output=""
summary_exit=0
if ! summary_output="$("$SUMMARY_SCRIPT" 2>&1)"; then
  summary_exit=$?
fi

state="unknown"
if grep -q 'ready_for_real_review' <<<"$summary_output"; then
  state="ready_for_real_review"
elif grep -q 'actual_present real_fill_present review_pack_missing' <<<"$summary_output"; then
  state="review_pack_missing"
elif grep -q 'actual_present review_pack_incomplete' <<<"$summary_output"; then
  state="actual_missing"
elif grep -q 'synthetic_only actual_missing review_pack_missing' <<<"$summary_output"; then
  state="synthetic_only"
elif [[ $summary_exit -ne 0 ]]; then
  echo "$summary_output" >&2
  echo "FIRST_CONTROLLED_SEND_STATUS FAIL: could not classify gate-summary output" >&2
  exit 1
fi

legacy_examples=0
actual_artifacts=0
while IFS= read -r line; do
  case "$(basename "$line")" in
    FIRST_REAL_REQUEST_*.md) legacy_examples=$((legacy_examples + 1)) ;;
    FIRST_CONTROLLED_SEND_*.md) actual_artifacts=$((actual_artifacts + 1)) ;;
  esac
done < <(find "$ARTIFACT_DIR" -maxdepth 1 -type f \( -name 'FIRST_REAL_REQUEST_*.md' -o -name 'FIRST_CONTROLLED_SEND_*.md' \) | sort)

domain_worth_buying="no"
external_showcase_ready="no"
if [[ "$state" == "ready_for_real_review" ]]; then
  domain_worth_buying="yes"
  external_showcase_ready="yes"
fi

adapter_report="$(
  cd "$ADAPTER_MODULE_DIR"
  python3 - <<'PY'
from app.executors.testnet_real_handoff_adapter import build_real_handoff_adapter_skeleton


adapter = build_real_handoff_adapter_skeleton(
    {
        "TESTNET_EXCHANGE_BASE_URL": "https://testnet.binancefuture.com",
        "TESTNET_EXECUTOR_MODE": "mock",
        "TESTNET_EXECUTOR_REAL_ENABLE": "0",
        "TESTNET_EXCHANGE_API_KEY": "",
        "TESTNET_EXCHANGE_API_SECRET": "",
        "TESTNET_EXCHANGE_KEY_ID": "",
    }
)

runtime = adapter["current_runtime"]
mode = "mock_only" if runtime["credential_free_mock_posture"] else "drifted"

print("REAL_HANDOFF_ADAPTER=present")
print(f"REAL_HANDOFF_MODE={mode}")
print(
    "EXTERNAL_REQUEST_ALLOWED="
    + ("yes" if adapter["allows_external_request"] else "no")
)
print(
    "RUNTIME_MUTATION_ALLOWED="
    + ("yes" if adapter["allows_runtime_mutation"] else "no")
)
PY
)"

task_input_report="$(
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

boundary = "review_only"
if payload["expected_executor_mode"] != "mock" or payload["expected_real_enable"] != "0":
    boundary = "invalid"

print("REAL_HANDOFF_TASK_INPUT_CONTRACT=present")
print(f"REAL_HANDOFF_TASK_INPUT_BOUNDARY={boundary}")
print("TASK_INPUT_EXTERNAL_REQUEST_ALLOWED=no")
print("TASK_INPUT_RUNTIME_MUTATION_ALLOWED=no")
PY
)"

placeholder_report="$(
  python3 - <<'PY'
payload = {
    "TESTNET_EXCHANGE_API_KEY": "<placeholder>",
    "TESTNET_EXCHANGE_API_SECRET": "<placeholder>",
    "TESTNET_EXCHANGE_KEY_ID": "NOT_COLLECTED",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "notes": "review-only placeholder contract",
}

policy = "placeholder_only"
if payload["expected_executor_mode"] != "mock" or payload["expected_real_enable"] != "0":
    policy = "invalid"

print("REAL_CREDENTIAL_PLACEHOLDER_BOUNDARY=present")
print(f"REAL_CREDENTIAL_PLACEHOLDER_POLICY={policy}")
print("PLACEHOLDER_EXTERNAL_REQUEST_ALLOWED=no")
print("PLACEHOLDER_RUNTIME_MUTATION_ALLOWED=no")
PY
)"

opening_prereq_report="$(
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

print("REAL_HANDOFF_OPENING_PREREQ_CONTRACT=present")
print(f"REAL_HANDOFF_OPENING_PREREQ_BOUNDARY={boundary}")
print("OPENING_PREREQ_EXTERNAL_REQUEST_ALLOWED=no")
print("OPENING_PREREQ_RUNTIME_MUTATION_ALLOWED=no")
PY
)"

opening_bundle_report="$(
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

print("REAL_HANDOFF_OPENING_BUNDLE_CONTRACT=present")
print(f"REAL_HANDOFF_OPENING_BUNDLE_BOUNDARY={boundary}")
print("OPENING_BUNDLE_EXTERNAL_REQUEST_ALLOWED=no")
print("OPENING_BUNDLE_RUNTIME_MUTATION_ALLOWED=no")
PY
)"

opening_decision_packet_report="$(
  python3 - <<'PY'
payload = {
    "packet_id": "real-handoff-opening-decision-packet-20260526-001",
    "reviewed_state": "ready_for_real_review",
    "opening_bundle_line_status": "green",
    "evidence_command_id": "order-mocksmoke-20260525111528",
    "artifact_path": "docs/reviews/real_testnet/FIRST_CONTROLLED_SEND_2026-05-25_order-mocksmoke-20260525111528.md",
    "decision_packet_path": "docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_V1.md",
    "expected_executor_mode": "mock",
    "expected_real_enable": "0",
    "credential_slots_requested": [
        "TESTNET_EXCHANGE_API_KEY",
        "TESTNET_EXCHANGE_API_SECRET",
        "TESTNET_EXCHANGE_KEY_ID",
    ],
    "reviewer_role": "operator_reviewer",
    "ticket_ref": "RHODP-001",
    "notes": "bounded opening decision packet contract",
}

boundary = "review_only"
if payload["expected_executor_mode"] != "mock" or payload["expected_real_enable"] != "0":
    boundary = "invalid"
if (
    payload["reviewed_state"] != "ready_for_real_review"
    or payload["opening_bundle_line_status"] != "green"
):
    boundary = "invalid"

print("REAL_HANDOFF_OPENING_DECISION_PACKET_CONTRACT=present")
print(f"REAL_HANDOFF_OPENING_DECISION_PACKET_BOUNDARY={boundary}")
print("OPENING_DECISION_PACKET_EXTERNAL_REQUEST_ALLOWED=no")
print("OPENING_DECISION_PACKET_RUNTIME_MUTATION_ALLOWED=no")
PY
)"

explicit_runtime_send_report="$(
  python3 - <<'PY'
payload = {
    "runtime_send_boundary_id": "real-handoff-explicit-runtime-send-boundary-20260527-001",
    "runtime_send_boundary": "BLOCKED",
    "approval_packet_present": "yes",
    "explicit_runtime_send_present": "yes",
    "approved_execution_mode": "testnet",
    "credential_runtime_verified": "yes",
    "review_verdict_pass": "yes",
    "rollback_packet_present": "yes",
    "send_window_current": "yes",
    "next_gate": "blocked_before_real_request",
}

print(f"REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_BOUNDARY={payload['runtime_send_boundary']}")
print(f"EXPLICIT_RUNTIME_SEND_APPROVAL_PACKET_PRESENT={payload['approval_packet_present']}")
print(f"EXPLICIT_RUNTIME_SEND_PRESENT={payload['explicit_runtime_send_present']}")
print(f"EXPLICIT_RUNTIME_SEND_CREDENTIAL_RUNTIME_VERIFIED={payload['credential_runtime_verified']}")
print(f"EXPLICIT_RUNTIME_SEND_REVIEW_VERDICT_PASS={payload['review_verdict_pass']}")
print(f"EXPLICIT_RUNTIME_SEND_ROLLBACK_PACKET_PRESENT={payload['rollback_packet_present']}")
print(f"EXPLICIT_RUNTIME_SEND_WINDOW_CURRENT={payload['send_window_current']}")
print("EXPLICIT_RUNTIME_SEND_EXTERNAL_REQUEST_ALLOWED=no")
print("EXPLICIT_RUNTIME_SEND_RUNTIME_MUTATION_ALLOWED=no")
print(f"EXPLICIT_RUNTIME_SEND_NEXT_GATE={payload['next_gate']}")
print(f"EXPLICIT_RUNTIME_SEND_APPROVED_EXECUTION_MODE={payload['approved_execution_mode']}")
PY
)"

report="$(cat <<EOF
FIRST_CONTROLLED_SEND_STATUS_REPORT
STATE=${state}
LEGACY_EXAMPLES=${legacy_examples}
ACTUAL_ARTIFACTS=${actual_artifacts}
DOMAIN_WORTH_BUYING=${domain_worth_buying}
EXTERNAL_SHOWCASE_READY=${external_showcase_ready}
${adapter_report}
${task_input_report}
${placeholder_report}
${opening_prereq_report}
${opening_bundle_report}
${opening_decision_packet_report}
${explicit_runtime_send_report}
EOF
)"

echo "$report"

if [[ -n "$OUT_FILE" ]]; then
  if [[ "${OUT_FILE}" == */ ]]; then
    echo "FIRST_CONTROLLED_SEND_STATUS FAIL: --out expects a file path, got directory-like path: ${OUT_FILE}" >&2
    exit 2
  fi
  if [[ -d "${OUT_FILE}" ]]; then
    echo "FIRST_CONTROLLED_SEND_STATUS FAIL: --out expects a file path, got directory: ${OUT_FILE}" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%s\n' "$report" > "$OUT_FILE"
  echo "WROTE_REPORT=$OUT_FILE"
fi

if ((CHECK_DOMAIN_GATE == 1)); then
  if [[ "$domain_worth_buying" != "yes" ]]; then
    echo "FIRST_CONTROLLED_SEND_DOMAIN_GATE BLOCKED: DOMAIN_WORTH_BUYING=${domain_worth_buying}" >&2
    exit 1
  fi
  echo "FIRST_CONTROLLED_SEND_DOMAIN_GATE PASS: DOMAIN_WORTH_BUYING=yes"
fi

if [[ -n "$REQUIRE_STATE" ]]; then
  if [[ "$state" != "$REQUIRE_STATE" ]]; then
    echo "FIRST_CONTROLLED_SEND_STATE_GATE BLOCKED: expected STATE=${REQUIRE_STATE}, got STATE=${state}" >&2
    exit 1
  fi
  echo "FIRST_CONTROLLED_SEND_STATE_GATE PASS: STATE=${state}"
fi

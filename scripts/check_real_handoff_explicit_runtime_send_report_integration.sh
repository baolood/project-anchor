#!/usr/bin/env bash
# Verifies that the standalone explicit-runtime-send evidence report agrees
# with the first-controlled-send status report on the hard-blocked review
# surface.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_explicit_runtime_send_report_integration.sh

Checks that:
- real_handoff_explicit_runtime_send_evidence_report.sh emits the bounded
  explicit-runtime-send evidence
- first_controlled_send_status_report.sh exposes the same hard-blocked posture
- both surfaces keep external requests, runtime mutation, and live trading
  disabled

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
  echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_REPORT_INTEGRATION FAIL: cannot resolve repository root" >&2
  exit 1
}

STATUS_SCRIPT="${ROOT}/scripts/first_controlled_send_status_report.sh"
EVIDENCE_SCRIPT="${ROOT}/scripts/real_handoff_explicit_runtime_send_evidence_report.sh"

fail() {
  echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_REPORT_INTEGRATION FAIL: $1" >&2
  exit 1
}

status_output="$("$STATUS_SCRIPT")"
evidence_output="$(bash "$EVIDENCE_SCRIPT")"

status_boundary="$(grep '^REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_BOUNDARY=' <<<"$status_output" | cut -d= -f2-)"
status_approval_packet="$(grep '^EXPLICIT_RUNTIME_SEND_APPROVAL_PACKET_PRESENT=' <<<"$status_output" | cut -d= -f2-)"
status_present="$(grep '^EXPLICIT_RUNTIME_SEND_PRESENT=' <<<"$status_output" | cut -d= -f2-)"
status_credential_runtime="$(grep '^EXPLICIT_RUNTIME_SEND_CREDENTIAL_RUNTIME_VERIFIED=' <<<"$status_output" | cut -d= -f2-)"
status_review_verdict="$(grep '^EXPLICIT_RUNTIME_SEND_REVIEW_VERDICT_PASS=' <<<"$status_output" | cut -d= -f2-)"
status_rollback_packet="$(grep '^EXPLICIT_RUNTIME_SEND_ROLLBACK_PACKET_PRESENT=' <<<"$status_output" | cut -d= -f2-)"
status_window="$(grep '^EXPLICIT_RUNTIME_SEND_WINDOW_CURRENT=' <<<"$status_output" | cut -d= -f2-)"
status_external_request="$(grep '^EXPLICIT_RUNTIME_SEND_EXTERNAL_REQUEST_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"
status_runtime_mutation="$(grep '^EXPLICIT_RUNTIME_SEND_RUNTIME_MUTATION_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"
status_next_gate="$(grep '^EXPLICIT_RUNTIME_SEND_NEXT_GATE=' <<<"$status_output" | cut -d= -f2-)"
status_execution_mode="$(grep '^EXPLICIT_RUNTIME_SEND_APPROVED_EXECUTION_MODE=' <<<"$status_output" | cut -d= -f2-)"

evidence_boundary="$(grep '^REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_BOUNDARY=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_approval_packet="$(grep '^EXPLICIT_RUNTIME_SEND_APPROVAL_PACKET_PRESENT=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_present="$(grep '^EXPLICIT_RUNTIME_SEND_PRESENT=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_credential_runtime="$(grep '^EXPLICIT_RUNTIME_SEND_CREDENTIAL_RUNTIME_VERIFIED=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_review_verdict="$(grep '^EXPLICIT_RUNTIME_SEND_REVIEW_VERDICT_PASS=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_rollback_packet="$(grep '^EXPLICIT_RUNTIME_SEND_ROLLBACK_PACKET_PRESENT=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_window="$(grep '^EXPLICIT_RUNTIME_SEND_WINDOW_CURRENT=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_external_request="$(grep '^EXPLICIT_RUNTIME_SEND_EXTERNAL_REQUEST_ALLOWED=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_runtime_mutation="$(grep '^EXPLICIT_RUNTIME_SEND_RUNTIME_MUTATION_ALLOWED=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_live_trading="$(grep '^EXPLICIT_RUNTIME_SEND_LIVE_TRADING_ALLOWED=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_next_gate="$(grep '^EXPLICIT_RUNTIME_SEND_NEXT_GATE=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_execution_mode="$(grep '^EXPLICIT_RUNTIME_SEND_APPROVED_EXECUTION_MODE=' <<<"$evidence_output" | cut -d= -f2-)"

[[ "$status_boundary" == "BLOCKED" ]] || fail "status report should keep explicit runtime send boundary hard-blocked"
[[ "$evidence_boundary" == "BLOCKED" ]] || fail "evidence report should keep explicit runtime send boundary hard-blocked"
[[ "$status_boundary" == "$evidence_boundary" ]] || fail "boundary drift between status and evidence reports"

[[ "$status_approval_packet" == "yes" ]] || fail "status report should keep approval packet present"
[[ "$evidence_approval_packet" == "yes" ]] || fail "evidence report should keep approval packet present"
[[ "$status_approval_packet" == "$evidence_approval_packet" ]] || fail "approval packet drift between status and evidence reports"

[[ "$status_present" == "yes" ]] || fail "status report should keep explicit runtime send present"
[[ "$evidence_present" == "yes" ]] || fail "evidence report should keep explicit runtime send present"
[[ "$status_present" == "$evidence_present" ]] || fail "explicit runtime send presence drift between status and evidence reports"

[[ "$status_credential_runtime" == "yes" ]] || fail "status report should keep credential runtime verified"
[[ "$evidence_credential_runtime" == "yes" ]] || fail "evidence report should keep credential runtime verified"
[[ "$status_credential_runtime" == "$evidence_credential_runtime" ]] || fail "credential runtime drift between status and evidence reports"

[[ "$status_review_verdict" == "yes" ]] || fail "status report should keep review verdict pass"
[[ "$evidence_review_verdict" == "yes" ]] || fail "evidence report should keep review verdict pass"
[[ "$status_review_verdict" == "$evidence_review_verdict" ]] || fail "review verdict drift between status and evidence reports"

[[ "$status_rollback_packet" == "yes" ]] || fail "status report should keep rollback packet present"
[[ "$evidence_rollback_packet" == "yes" ]] || fail "evidence report should keep rollback packet present"
[[ "$status_rollback_packet" == "$evidence_rollback_packet" ]] || fail "rollback packet drift between status and evidence reports"

[[ "$status_window" == "yes" ]] || fail "status report should keep send window current"
[[ "$evidence_window" == "yes" ]] || fail "evidence report should keep send window current"
[[ "$status_window" == "$evidence_window" ]] || fail "send window drift between status and evidence reports"

[[ "$status_external_request" == "no" ]] || fail "status report must keep external requests disabled"
[[ "$evidence_external_request" == "no" ]] || fail "evidence report must keep external requests disabled"
[[ "$status_external_request" == "$evidence_external_request" ]] || fail "external-request flag drift between status and evidence reports"

[[ "$status_runtime_mutation" == "no" ]] || fail "status report must keep runtime mutation disabled"
[[ "$evidence_runtime_mutation" == "no" ]] || fail "evidence report must keep runtime mutation disabled"
[[ "$status_runtime_mutation" == "$evidence_runtime_mutation" ]] || fail "runtime-mutation flag drift between status and evidence reports"

[[ "$evidence_live_trading" == "no" ]] || fail "evidence report must keep live trading disabled"

[[ "$status_next_gate" == "blocked_before_real_request" ]] || fail "status report should keep next gate blocked_before_real_request"
[[ "$evidence_next_gate" == "blocked_before_real_request" ]] || fail "evidence report should keep next gate blocked_before_real_request"
[[ "$status_next_gate" == "$evidence_next_gate" ]] || fail "next-gate drift between status and evidence reports"

[[ "$status_execution_mode" == "testnet" ]] || fail "status report should keep approved execution mode testnet"
[[ "$evidence_execution_mode" == "testnet" ]] || fail "evidence report should keep approved execution mode testnet"
[[ "$status_execution_mode" == "$evidence_execution_mode" ]] || fail "approved-execution-mode drift between status and evidence reports"

echo "REAL_HANDOFF_EXPLICIT_RUNTIME_SEND_REPORT_INTEGRATION PASS: review surfaces aligned"

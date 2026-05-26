#!/usr/bin/env bash
# Verifies that the standalone real handoff opening-prereq evidence report
# agrees with the first-controlled-send status report on the bounded
# review-only contract surface.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_handoff_opening_prereq_report_integration.sh

Checks that:
- real_handoff_opening_prereq_evidence_report.sh emits the bounded opening-prereq evidence
- first_controlled_send_status_report.sh exposes the same review-only posture
- both surfaces keep external requests, runtime mutation, and live trading disabled

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
  echo "REAL_HANDOFF_OPENING_PREREQ_REPORT_INTEGRATION FAIL: cannot resolve repository root" >&2
  exit 1
}

STATUS_SCRIPT="${ROOT}/scripts/first_controlled_send_status_report.sh"
EVIDENCE_SCRIPT="${ROOT}/scripts/real_handoff_opening_prereq_evidence_report.sh"

fail() {
  echo "REAL_HANDOFF_OPENING_PREREQ_REPORT_INTEGRATION FAIL: $1" >&2
  exit 1
}

status_output="$("$STATUS_SCRIPT")"
evidence_output="$(bash "$EVIDENCE_SCRIPT")"

status_contract="$(grep '^REAL_HANDOFF_OPENING_PREREQ_CONTRACT=' <<<"$status_output" | cut -d= -f2-)"
status_boundary="$(grep '^REAL_HANDOFF_OPENING_PREREQ_BOUNDARY=' <<<"$status_output" | cut -d= -f2-)"
status_external_request="$(grep '^OPENING_PREREQ_EXTERNAL_REQUEST_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"
status_runtime_mutation="$(grep '^OPENING_PREREQ_RUNTIME_MUTATION_ALLOWED=' <<<"$status_output" | cut -d= -f2-)"

evidence_contract="$(grep '^REAL_HANDOFF_OPENING_PREREQ_CONTRACT=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_boundary="$(grep '^REAL_HANDOFF_OPENING_PREREQ_BOUNDARY=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_external_request="$(grep '^OPENING_PREREQ_EXTERNAL_REQUEST_ALLOWED=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_runtime_mutation="$(grep '^OPENING_PREREQ_RUNTIME_MUTATION_ALLOWED=' <<<"$evidence_output" | cut -d= -f2-)"
evidence_live_trading="$(grep '^OPENING_PREREQ_LIVE_TRADING_ALLOWED=' <<<"$evidence_output" | cut -d= -f2-)"

[[ "$status_contract" == "present" ]] || fail "status report should expose real handoff opening prereq contract"
[[ "$evidence_contract" == "present" ]] || fail "evidence report should expose real handoff opening prereq contract"
[[ "$status_contract" == "$evidence_contract" ]] || fail "contract presence drift between status and evidence reports"

[[ "$status_boundary" == "review_only" ]] || fail "status report should stay review_only"
[[ "$evidence_boundary" == "review_only" ]] || fail "evidence report should stay review_only"
[[ "$status_boundary" == "$evidence_boundary" ]] || fail "boundary drift between status and evidence reports"

[[ "$status_external_request" == "no" ]] || fail "status report must keep external requests disabled"
[[ "$evidence_external_request" == "no" ]] || fail "evidence report must keep external requests disabled"
[[ "$status_external_request" == "$evidence_external_request" ]] || fail "external-request flag drift between status and evidence reports"

[[ "$status_runtime_mutation" == "no" ]] || fail "status report must keep runtime mutation disabled"
[[ "$evidence_runtime_mutation" == "no" ]] || fail "evidence report must keep runtime mutation disabled"
[[ "$status_runtime_mutation" == "$evidence_runtime_mutation" ]] || fail "runtime-mutation flag drift between status and evidence reports"

[[ "$evidence_live_trading" == "no" ]] || fail "evidence report must keep live trading disabled"

echo "REAL_HANDOFF_OPENING_PREREQ_REPORT_INTEGRATION PASS: review surfaces aligned"

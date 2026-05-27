#!/usr/bin/env bash
# Verifies the first-controlled-send scheduling decision record remains
# bounded, docs-only, and downstream of the readiness review surface.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_scheduling_decision_record.sh

Checks that the first-controlled-send scheduling decision record remains
coherent as a bounded docs-only decision surface before any actual scheduling
or real external request can be considered.

This script verifies:
- the readiness-review check remains green
- the scheduling-decision-record doc and its bounded source docs exist
- the decision record stays fixed to ORDER + execution_mode=testnet
- the decision record still records schedule-or-block rather than scheduling
- the downstream decision bundle still points at the scheduling decision record

This script does not inject credentials, mutate runtime, schedule a send,
issue external requests, or authorize live trading.
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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_READINESS_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_readiness_review.sh"
DECISION_RECORD_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md"
DECISION_BUNDLE_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_V1.md"

declare -a REQUIRED_DOCS=(
  "${DECISION_RECORD_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_DECISION_GATE_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_PACKET_V1.md"
  "${DECISION_BUNDLE_DOC}"
)

fail() {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_CHECK FAIL: $1" >&2
  exit 1
}

"${UPSTREAM_READINESS_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** scheduling decision record only - no real key, no external API call in this round, no live trading approval.' "${DECISION_RECORD_DOC}" \
  || fail "decision record doc must remain docs-only and request-free"

grep -Fq 'Command.type = ORDER' "${DECISION_RECORD_DOC}" \
  || fail "decision record doc must stay on canonical ORDER path"

grep -Fq 'payload.execution_mode = testnet' "${DECISION_RECORD_DOC}" \
  || fail "decision record doc must stay on canonical execution_mode=testnet path"

grep -Fq 'This document does not schedule the send by itself.' "${DECISION_RECORD_DOC}" \
  || fail "decision record doc must keep scheduling blocked by itself"

grep -Fq 'did the project schedule the first controlled send,' "${DECISION_RECORD_DOC}" \
  || fail "decision record doc must keep schedule-or-block scope"

grep -Fq 'live trading remains `NO-GO`' "${DECISION_RECORD_DOC}" \
  || fail "decision record labels must keep live trading NO-GO"

grep -Fq 'docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must still point to the scheduling decision record"

grep -Fq 'readiness review and decision record now form the final pre-scheduling decision surface' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must keep the bounded pre-scheduling decision surface statement"

echo "FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD=PASS"
echo "CANONICAL_PATH=ORDER:testnet"
echo "DECISION_RECORD_STATUS=docs_only"
echo "SCHEDULING_ALLOWED=no"
echo "DECISION_OUTCOME_SURFACE=schedule_or_block_record_only"
echo "MAIN_BLOCKER=real_runtime_window_proof_and_actual_review_evidence"
echo "EXTERNAL_REQUEST_ATTEMPTED=no"
echo "LIVE_TRADING=NO-GO"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_CHECK PASS: scheduling decision record remains bounded, docs-only, and blocked before scheduling"

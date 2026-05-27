#!/usr/bin/env bash
# Verifies the first-controlled-send decision bundle remains bounded,
# docs-only, and blocked before any actual scheduling or real request.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_decision_bundle.sh

Checks that the first-controlled-send decision bundle remains coherent as a
bounded docs-only pre-scheduling decision surface before any actual scheduling
or real external request can be considered.

This script verifies:
- the scheduling-decision-record check remains green
- the decision-bundle doc and its bounded source docs exist
- the decision bundle stays fixed to ORDER + execution_mode=testnet
- the decision bundle still acts as a review entrypoint rather than scheduling
- live trading remains NO-GO and the first controlled send remains blocked

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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_DECISION_RECORD_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_scheduling_decision_record.sh"
DECISION_BUNDLE_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_V1.md"
DECISION_BUNDLE_CLOSEOUT_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CLOSEOUT_V1.md"

declare -a REQUIRED_DOCS=(
  "${DECISION_BUNDLE_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_GATE_BUNDLE_CLOSEOUT_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_GATE_BUNDLE_V1.md"
  "${DECISION_BUNDLE_CLOSEOUT_DOC}"
)

fail() {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CHECK FAIL: $1" >&2
  exit 1
}

"${UPSTREAM_DECISION_RECORD_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** decision-bundle only - no real key, no external API call in this round, no live trading approval.' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must remain docs-only and request-free"

grep -Fq 'Command.type = ORDER' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must stay on canonical ORDER path"

grep -Fq 'payload.execution_mode = testnet' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must stay on canonical execution_mode=testnet path"

grep -Fq 'This bundle does not schedule the send by itself.' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must keep scheduling blocked by itself"

grep -Fq 'Read the final pre-scheduling decision stack in this order.' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must keep a bounded reading order"

grep -Fq 'Does the decision still preserve live-trading `NO-GO` and one-send-only discipline?' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must preserve live-trading NO-GO and one-send-only discipline"

grep -Fq 'readiness review and decision record now form the final pre-scheduling decision surface' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must keep the bounded pre-scheduling decision surface statement"

grep -Fq 'first-controlled-send pre-scheduling decision bundle: COMPLETE as docs-only stack' "${DECISION_BUNDLE_CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must keep the docs-only complete status statement"

grep -Fq 'actual first controlled send: not yet scheduled or attempted' "${DECISION_BUNDLE_CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must keep the first controlled send blocked"

grep -Fq 'live trading: NO-GO' "${DECISION_BUNDLE_CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must keep live trading NO-GO"

echo "FIRST_CONTROLLED_SEND_DECISION_BUNDLE=PASS"
echo "CANONICAL_PATH=ORDER:testnet"
echo "DECISION_BUNDLE_STATUS=docs_only"
echo "SCHEDULING_ALLOWED=no"
echo "DECISION_STACK=bounded_pre_scheduling_bundle"
echo "ACTUAL_FIRST_CONTROLLED_SEND=not_yet_scheduled_or_attempted"
echo "MAIN_BLOCKER=real_runtime_window_proof_and_actual_review_evidence"
echo "EXTERNAL_REQUEST_ATTEMPTED=no"
echo "LIVE_TRADING=NO-GO"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CHECK PASS: decision bundle remains bounded, docs-only, and blocked before scheduling"

#!/usr/bin/env bash
# Verifies the first-controlled-send decision-bundle closeout remains bounded,
# docs-only, and blocked before any actual scheduling or real request.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_decision_bundle_closeout.sh

Checks that the first-controlled-send decision-bundle closeout remains coherent
as a bounded docs-only closeout surface before any actual scheduling or real
external request can be considered.

This script verifies:
- the decision-bundle check remains green
- the decision-bundle closeout doc and its bounded source docs exist
- the closeout remains docs-only and request-free
- the closeout still states the first controlled send is not yet scheduled or attempted
- live trading remains NO-GO

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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CLOSEOUT_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_DECISION_BUNDLE_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_decision_bundle.sh"
CLOSEOUT_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CLOSEOUT_V1.md"

declare -a REQUIRED_DOCS=(
  "${CLOSEOUT_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_GATE_BUNDLE_CLOSEOUT_V1.md"
)

fail() {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CLOSEOUT_CHECK FAIL: $1" >&2
  exit 1
}

"${UPSTREAM_DECISION_BUNDLE_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** closeout only - no real key, no external API call in this round, no live trading approval.' "${CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must remain docs-only and request-free"

grep -Fq 'This closeout does not schedule the send.' "${CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must keep scheduling blocked by itself"

grep -Fq 'READY FOR FIRST CONTROLLED SEND DECISION' "${CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must keep the interpretation label"

grep -Fq 'first-controlled-send pre-scheduling decision bundle: COMPLETE as docs-only stack' "${CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must keep the docs-only complete status statement"

grep -Fq 'actual first controlled send: not yet scheduled or attempted' "${CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must keep the first controlled send blocked"

grep -Fq 'main blocker: real runtime-window proof and actual review evidence' "${CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must keep the current blocker statement"

grep -Fq 'live trading: NO-GO' "${CLOSEOUT_DOC}" \
  || fail "decision bundle closeout doc must keep live trading NO-GO"

echo "FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CLOSEOUT=PASS"
echo "INTERPRETATION_LABEL=READY_FOR_FIRST_CONTROLLED_SEND_DECISION"
echo "DECISION_BUNDLE_CLOSEOUT=COMPLETE_DOCS_ONLY"
echo "ACTUAL_FIRST_CONTROLLED_SEND=not_yet_scheduled_or_attempted"
echo "MAIN_BLOCKER=real_runtime_window_proof_and_actual_review_evidence"
echo "EXTERNAL_REQUEST_ATTEMPTED=no"
echo "LIVE_TRADING=NO-GO"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CLOSEOUT_CHECK PASS: decision bundle closeout remains coherent, docs-only, and blocked before scheduling"

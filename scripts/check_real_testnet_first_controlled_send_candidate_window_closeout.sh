#!/usr/bin/env bash
# Verifies the first-controlled-send candidate-window closeout remains bounded,
# docs-only, and blocked before any actual window open or real request.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_candidate_window_closeout.sh

Checks that the first-controlled-send candidate-window closeout remains
coherent as a bounded docs-only bridge before any actual window open or real
external request can be considered.

This script verifies:
- the candidate-window-record check remains green
- the candidate-window closeout doc and its bounded source docs exist
- the closeout remains docs-only and request-free
- the closeout still states the first controlled send is not yet window-opened or attempted
- live trading remains NO-GO

This script does not inject credentials, mutate runtime, open a window,
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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_CLOSEOUT_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_CANDIDATE_WINDOW_RECORD_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_candidate_window_record.sh"
CLOSEOUT_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_CLOSEOUT_V1.md"

declare -a REQUIRED_DOCS=(
  "${CLOSEOUT_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULE_PACKET_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md"
)

fail() {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_CLOSEOUT_CHECK FAIL: $1" >&2
  exit 1
}

"${UPSTREAM_CANDIDATE_WINDOW_RECORD_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** closeout only - no real key, no external API call in this round, no live trading approval.' "${CLOSEOUT_DOC}" \
  || fail "candidate-window closeout doc must remain docs-only and request-free"

grep -Fq 'This closeout does not open the window or execute the send.' "${CLOSEOUT_DOC}" \
  || fail "candidate-window closeout doc must keep window opening and execution blocked by itself"

grep -Fq 'READY FOR WINDOW OPEN CANDIDATE' "${CLOSEOUT_DOC}" \
  || fail "candidate-window closeout doc must keep the interpretation label"

grep -Fq 'first-controlled-send candidate-window layer: COMPLETE as docs-only bridge' "${CLOSEOUT_DOC}" \
  || fail "candidate-window closeout doc must keep the docs-only bridge status statement"

grep -Fq 'actual first controlled send: not yet window-opened or attempted' "${CLOSEOUT_DOC}" \
  || fail "candidate-window closeout doc must keep the first controlled send blocked"

grep -Fq 'main blocker: real runtime-window proof and actual review evidence' "${CLOSEOUT_DOC}" \
  || fail "candidate-window closeout doc must keep the current blocker statement"

grep -Fq 'live trading: NO-GO' "${CLOSEOUT_DOC}" \
  || fail "candidate-window closeout doc must keep live trading NO-GO"

echo "FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_CLOSEOUT=PASS"
echo "INTERPRETATION_LABEL=READY_FOR_WINDOW_OPEN_CANDIDATE"
echo "CANDIDATE_WINDOW_CLOSEOUT=COMPLETE_DOCS_ONLY"
echo "ACTUAL_FIRST_CONTROLLED_SEND=not_yet_window_opened_or_attempted"
echo "MAIN_BLOCKER=real_runtime_window_proof_and_actual_review_evidence"
echo "EXTERNAL_REQUEST_ATTEMPTED=no"
echo "LIVE_TRADING=NO-GO"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_CLOSEOUT_CHECK PASS: candidate-window closeout remains coherent, docs-only, and blocked before window opening"

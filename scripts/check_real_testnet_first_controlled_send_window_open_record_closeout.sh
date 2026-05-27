#!/usr/bin/env bash
# Verifies the first-controlled-send window-open-record closeout remains
# bounded, docs-only, and blocked before any actual send attempt.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_window_open_record_closeout.sh

Checks that the first-controlled-send window-open-record closeout remains
coherent as a bounded docs-only transition posture before any actual send
attempt or real external request can be considered.

This script verifies:
- the window-open-record check remains green
- the window-open-record closeout doc and its bounded source docs exist
- the closeout remains docs-only and request-free
- the closeout still states the first controlled send is not yet attempted inside a real opened window
- live trading remains NO-GO

This script does not inject credentials, mutate runtime, open a window,
attempt a send, issue external requests, or authorize live trading.
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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_CLOSEOUT_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_WINDOW_OPEN_RECORD_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_window_open_record.sh"
CLOSEOUT_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_CLOSEOUT_V1.md"

declare -a REQUIRED_DOCS=(
  "${CLOSEOUT_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CHECKLIST_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md"
)

fail() {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_CLOSEOUT_CHECK FAIL: $1" >&2
  exit 1
}

"${UPSTREAM_WINDOW_OPEN_RECORD_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** closeout only - no real key, no external API call in this round, no live trading approval.' "${CLOSEOUT_DOC}" \
  || fail "window-open-record closeout doc must remain docs-only and request-free"

grep -Fq 'This closeout does not open the window or execute the send.' "${CLOSEOUT_DOC}" \
  || fail "window-open-record closeout doc must keep window opening and execution blocked by itself"

grep -Fq 'READY FOR OPENED-WINDOW FACTS' "${CLOSEOUT_DOC}" \
  || fail "window-open-record closeout doc must keep the interpretation label"

grep -Fq 'first-controlled-send window-open record layer: COMPLETE as docs-only posture' "${CLOSEOUT_DOC}" \
  || fail "window-open-record closeout doc must keep the docs-only posture status statement"

grep -Fq 'actual first controlled send: not yet attempted inside a real opened window' "${CLOSEOUT_DOC}" \
  || fail "window-open-record closeout doc must keep the first controlled send blocked"

grep -Fq 'main blocker: real opened-window runtime proof and actual review evidence' "${CLOSEOUT_DOC}" \
  || fail "window-open-record closeout doc must keep the current blocker statement"

grep -Fq 'live trading: NO-GO' "${CLOSEOUT_DOC}" \
  || fail "window-open-record closeout doc must keep live trading NO-GO"

echo "FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_CLOSEOUT=PASS"
echo "INTERPRETATION_LABEL=READY_FOR_OPENED_WINDOW_FACTS"
echo "WINDOW_OPEN_RECORD_CLOSEOUT=COMPLETE_DOCS_ONLY"
echo "ACTUAL_FIRST_CONTROLLED_SEND=not_yet_attempted_inside_real_opened_window"
echo "MAIN_BLOCKER=real_opened_window_runtime_proof_and_actual_review_evidence"
echo "EXTERNAL_REQUEST_ATTEMPTED=no"
echo "LIVE_TRADING=NO-GO"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_CLOSEOUT_CHECK PASS: window-open-record closeout remains coherent, docs-only, and blocked before any send attempt"

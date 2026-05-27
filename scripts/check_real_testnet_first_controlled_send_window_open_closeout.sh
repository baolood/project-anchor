#!/usr/bin/env bash
# Verifies the first-controlled-send window-open closeout remains bounded,
# docs-only, and blocked before any actual window open or real request.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_window_open_closeout.sh

Checks that the first-controlled-send window-open closeout remains coherent as
a bounded docs-only opening posture before any actual window open or real
external request can be considered.

This script verifies:
- the window-open-checklist check remains green
- the window-open closeout doc and its bounded source docs exist
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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CLOSEOUT_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_WINDOW_OPEN_CHECKLIST_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_window_open_checklist.sh"
CLOSEOUT_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CLOSEOUT_V1.md"

declare -a REQUIRED_DOCS=(
  "${CLOSEOUT_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CHECKLIST_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md"
  "${ROOT}/docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md"
)

fail() {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CLOSEOUT_CHECK FAIL: $1" >&2
  exit 1
}

"${UPSTREAM_WINDOW_OPEN_CHECKLIST_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** closeout only - no real key, no external API call in this round, no live trading approval.' "${CLOSEOUT_DOC}" \
  || fail "window-open closeout doc must remain docs-only and request-free"

grep -Fq 'This closeout does not open the window or execute the send.' "${CLOSEOUT_DOC}" \
  || fail "window-open closeout doc must keep window opening and execution blocked by itself"

grep -Fq 'READY FOR WINDOW OPEN' "${CLOSEOUT_DOC}" \
  || fail "window-open closeout doc must keep the interpretation label"

grep -Fq 'first-controlled-send window-open layer: COMPLETE as docs-only posture' "${CLOSEOUT_DOC}" \
  || fail "window-open closeout doc must keep the docs-only posture status statement"

grep -Fq 'actual first controlled send: not yet window-opened or attempted' "${CLOSEOUT_DOC}" \
  || fail "window-open closeout doc must keep the first controlled send blocked"

grep -Fq 'main blocker: real runtime-window proof and actual review evidence' "${CLOSEOUT_DOC}" \
  || fail "window-open closeout doc must keep the current blocker statement"

grep -Fq 'live trading: NO-GO' "${CLOSEOUT_DOC}" \
  || fail "window-open closeout doc must keep live trading NO-GO"

echo "FIRST_CONTROLLED_SEND_WINDOW_OPEN_CLOSEOUT=PASS"
echo "INTERPRETATION_LABEL=READY_FOR_WINDOW_OPEN"
echo "WINDOW_OPEN_CLOSEOUT=COMPLETE_DOCS_ONLY"
echo "ACTUAL_FIRST_CONTROLLED_SEND=not_yet_window_opened_or_attempted"
echo "MAIN_BLOCKER=real_runtime_window_proof_and_actual_review_evidence"
echo "EXTERNAL_REQUEST_ATTEMPTED=no"
echo "LIVE_TRADING=NO-GO"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CLOSEOUT_CHECK PASS: window-open closeout remains coherent, docs-only, and blocked before window opening"

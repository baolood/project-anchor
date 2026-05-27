#!/usr/bin/env bash
# Verifies the docs-only first-real-request gate-bundle closeout remains
# bounded, coherent, and blocked before any actual controlled send.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_real_request_gate_bundle_closeout.sh

Checks that the first-real-request gate-bundle closeout remains coherent as a
docs-only decision stack and still blocks any actual controlled send.

This script verifies:
- the explicit runtime send line remains closed and hard-blocked
- the required scheduling/gate/runtime/evidence docs exist
- the gate-bundle closeout doc still states READY FOR CONTROLLED SEND GATE REVIEW
- the actual first controlled send remains not yet attempted
- live trading remains NO-GO

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
  echo "REAL_TESTNET_FIRST_REAL_REQUEST_GATE_BUNDLE_CLOSEOUT_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

RUNTIME_SEND_LINE="${ROOT}/scripts/check_real_handoff_explicit_runtime_send_line.sh"
CLOSEOUT_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_GATE_BUNDLE_CLOSEOUT_V1.md"

declare -a REQUIRED_DOCS=(
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_CONTROLLED_ATTEMPT_PREREQ_CHECK_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_PACKET_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_DECISION_GATE_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_GATE_BUNDLE_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md"
  "${ROOT}/docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md"
  "${ROOT}/docs/CLOUD_HOST_ACCESS_RETREAT_DRILL_SPEC_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EVIDENCE_BUNDLE_INDEX_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_REVIEW_CLOSEOUT_V1.md"
  "${CLOSEOUT_DOC}"
)

fail() {
  echo "REAL_TESTNET_FIRST_REAL_REQUEST_GATE_BUNDLE_CLOSEOUT_CHECK FAIL: $1" >&2
  exit 1
}

"${RUNTIME_SEND_LINE}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq 'READY FOR CONTROLLED SEND GATE REVIEW' "${CLOSEOUT_DOC}" \
  || fail "closeout doc must keep interpretation label READY FOR CONTROLLED SEND GATE REVIEW"

grep -Fq 'first-real-request pre-window gate bundle: COMPLETE as docs-only stack' "${CLOSEOUT_DOC}" \
  || fail "closeout doc must keep docs-only stack complete status statement"

grep -Fq 'actual first controlled send: not yet attempted' "${CLOSEOUT_DOC}" \
  || fail "closeout doc must keep actual first controlled send blocked as not yet attempted"

grep -Fq 'live trading: NO-GO' "${CLOSEOUT_DOC}" \
  || fail "closeout doc must keep live trading NO-GO"

echo "FIRST_REAL_REQUEST_GATE_BUNDLE_CLOSEOUT=PASS"
echo "INTERPRETATION_LABEL=READY_FOR_CONTROLLED_SEND_GATE_REVIEW"
echo "PRE_WINDOW_GATE_BUNDLE=COMPLETE_DOCS_ONLY"
echo "ACTUAL_FIRST_CONTROLLED_SEND=not_yet_attempted"
echo "MAIN_BLOCKER=real_runtime_window_proof_and_actual_review_evidence"
echo "LIVE_TRADING=NO-GO"
echo "REAL_TESTNET_FIRST_REAL_REQUEST_GATE_BUNDLE_CLOSEOUT_CHECK PASS: docs-only pre-window gate bundle remains coherent and blocked"

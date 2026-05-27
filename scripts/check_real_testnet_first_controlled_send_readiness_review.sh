#!/usr/bin/env bash
# Verifies the first-controlled-send readiness review remains bounded,
# review-only, and anchored to the upstream docs-only gate stack.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_readiness_review.sh

Checks that the first-controlled-send readiness review remains coherent as a
bounded docs-only review surface before any scheduling or real external
request can be considered.

This script verifies:
- the first-real-request gate bundle closeout remains green
- the readiness-review doc and its bounded source docs exist
- the readiness review stays fixed to ORDER + execution_mode=testnet
- the readiness review still blocks scheduling unless every answer is yes
- the downstream decision bundle still points at the readiness review

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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_GATE_CHECK="${ROOT}/scripts/check_real_testnet_first_real_request_gate_bundle_closeout.sh"
READINESS_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md"
DECISION_BUNDLE_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_V1.md"

declare -a REQUIRED_DOCS=(
  "${READINESS_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_GATE_BUNDLE_CLOSEOUT_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_GATE_BUNDLE_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_PACKET_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_DECISION_GATE_V1.md"
  "${ROOT}/docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md"
  "${DECISION_BUNDLE_DOC}"
)

fail() {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_CHECK FAIL: $1" >&2
  exit 1
}

"${UPSTREAM_GATE_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** readiness review only - no real key, no external API call in this round, no live trading approval.' "${READINESS_DOC}" \
  || fail "readiness review doc must remain review-only and request-free"

grep -Fq 'Command.type = ORDER' "${READINESS_DOC}" \
  || fail "readiness review doc must stay on canonical ORDER path"

grep -Fq 'payload.execution_mode = testnet' "${READINESS_DOC}" \
  || fail "readiness review doc must stay on canonical execution_mode=testnet path"

grep -Fq 'BLOCKED - do not schedule the first controlled send' "${READINESS_DOC}" \
  || fail "readiness review doc must keep the blocked-do-not-schedule guard"

grep -Fq 'The reviewer must be able to answer **yes** to all of these.' "${READINESS_DOC}" \
  || fail "readiness review doc must keep the all-yes readiness threshold"

grep -Fq 'live trading remains `NO-GO`' "${READINESS_DOC}" \
  || fail "readiness review decision labels must keep live trading NO-GO"

grep -Fq 'Read the final pre-scheduling decision stack in this order.' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must still present a bounded reading order"

grep -Fq 'docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md' "${DECISION_BUNDLE_DOC}" \
  || fail "decision bundle doc must still point to the readiness review"

echo "FIRST_CONTROLLED_SEND_READINESS_REVIEW=PASS"
echo "CANONICAL_PATH=ORDER:testnet"
echo "READINESS_REVIEW_STATUS=review_only"
echo "SCHEDULING_ALLOWED=no"
echo "DECISION_SURFACE=bounded_pre_scheduling_review"
echo "MAIN_BLOCKER=real_runtime_window_proof_and_actual_review_evidence"
echo "EXTERNAL_REQUEST_ATTEMPTED=no"
echo "LIVE_TRADING=NO-GO"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_CHECK PASS: readiness review remains bounded, review-only, and blocked before scheduling"

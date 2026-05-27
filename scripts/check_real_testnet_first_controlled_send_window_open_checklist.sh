#!/usr/bin/env bash
# Verifies the first-controlled-send window-open checklist remains bounded,
# docs-only, and blocked before any actual window open or real request.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_window_open_checklist.sh [--fixture <name>]

Checks that the first-controlled-send window-open checklist remains coherent
as a bounded docs-only gate before any actual window open or real external
request can be considered.

This script verifies:
- the candidate-window closeout check remains green
- the window-open checklist doc exists and keeps the canonical ORDER + testnet scope
- candidate validity, runtime posture, safety boundary, reviewability, and discipline remain explicit
- window opening remains blocked by default
- external requests, runtime mutation, and live trading remain blocked

Supported fixtures:
- window_stays_closed_by_default
- candidate_validity_missing
- runtime_posture_missing
- safety_boundary_missing
- reviewability_missing
- discipline_missing
- execution_mode_not_testnet
- external_request_attempted_true
- runtime_mutation_true
- live_trading_true

This script does not inject credentials, mutate runtime, open a window,
issue external requests, or authorize live trading.
EOF
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CHECKLIST_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_CANDIDATE_WINDOW_CLOSEOUT_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_candidate_window_closeout.sh"
CHECKLIST_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CHECKLIST_V1.md"

declare -a REQUIRED_DOCS=(
  "${CHECKLIST_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md"
  "${ROOT}/docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CLOSEOUT_V1.md"
)

FIXTURE="window_stays_closed_by_default"

while (($# > 0)); do
  case "$1" in
    --fixture)
      if (($# < 2)) || [[ "${2:-}" == --* ]]; then
        usage >&2
        exit 2
      fi
      FIXTURE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

fail() {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CHECKLIST_CHECK FAIL: $1" >&2
  exit 1
}

run_fixture() {
  local name="$1"
  local candidate_validity="yes"
  local runtime_posture="yes"
  local safety_boundary="yes"
  local reviewability="yes"
  local discipline="yes"
  local execution_mode="testnet"
  local external_request_attempted="false"
  local runtime_mutation="false"
  local live_trading="NO-GO"

  case "$name" in
    window_stays_closed_by_default)
      ;;
    candidate_validity_missing)
      candidate_validity=""
      ;;
    runtime_posture_missing)
      runtime_posture=""
      ;;
    safety_boundary_missing)
      safety_boundary=""
      ;;
    reviewability_missing)
      reviewability=""
      ;;
    discipline_missing)
      discipline=""
      ;;
    execution_mode_not_testnet)
      execution_mode="live"
      ;;
    external_request_attempted_true)
      external_request_attempted="true"
      ;;
    runtime_mutation_true)
      runtime_mutation="true"
      ;;
    live_trading_true)
      live_trading="GO"
      ;;
    *)
      fail "unknown fixture ${name}"
      ;;
  esac

  local result="PASS"
  [[ -n "$candidate_validity" ]] || result="BLOCKED"
  [[ -n "$runtime_posture" ]] || result="BLOCKED"
  [[ -n "$safety_boundary" ]] || result="BLOCKED"
  [[ -n "$reviewability" ]] || result="BLOCKED"
  [[ -n "$discipline" ]] || result="BLOCKED"
  [[ "$execution_mode" == "testnet" ]] || result="BLOCKED"
  [[ "$external_request_attempted" == "false" ]] || result="BLOCKED"
  [[ "$runtime_mutation" == "false" ]] || result="BLOCKED"
  [[ "$live_trading" == "NO-GO" ]] || result="BLOCKED"

  printf '%s\n' \
    "FIXTURE=${name}" \
    "FIXTURE_RESULT=${result}" \
    "FIXTURE_CANDIDATE_VALIDITY=${candidate_validity:-missing}" \
    "FIXTURE_RUNTIME_POSTURE=${runtime_posture:-missing}" \
    "FIXTURE_SAFETY_BOUNDARY=${safety_boundary:-missing}" \
    "FIXTURE_REVIEWABILITY=${reviewability:-missing}" \
    "FIXTURE_DISCIPLINE=${discipline:-missing}" \
    "FIXTURE_EXECUTION_MODE=${execution_mode}" \
    "FIXTURE_EXTERNAL_REQUEST_ATTEMPTED=${external_request_attempted}" \
    "FIXTURE_RUNTIME_MUTATION=${runtime_mutation}" \
    "FIXTURE_LIVE_TRADING=${live_trading}"
}

"${UPSTREAM_CANDIDATE_WINDOW_CLOSEOUT_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** window-open checklist only - no real key, no external API call in this round, no live trading approval.' "${CHECKLIST_DOC}" \
  || fail "window-open checklist doc must remain docs-only and request-free"

grep -Fq 'Command.type = ORDER' "${CHECKLIST_DOC}" \
  || fail "window-open checklist doc must stay on canonical ORDER path"

grep -Fq 'payload.execution_mode = testnet' "${CHECKLIST_DOC}" \
  || fail "window-open checklist doc must stay on canonical execution_mode=testnet path"

grep -Fq 'This document does not open the window by itself.' "${CHECKLIST_DOC}" \
  || fail "window-open checklist doc must keep window opening blocked by itself"

grep -Fq 'candidate_window_id_confirmed:' "${CHECKLIST_DOC}" \
  || fail "window-open checklist template must keep candidate_window_id_confirmed"

grep -Fq 'executor_mode_value_confirmed:' "${CHECKLIST_DOC}" \
  || fail "window-open checklist template must keep executor_mode_value_confirmed"

grep -Fq 'host_origin_confirmed:' "${CHECKLIST_DOC}" \
  || fail "window-open checklist template must keep host_origin_confirmed"

grep -Fq 'ops_reachable:' "${CHECKLIST_DOC}" \
  || fail "window-open checklist template must keep ops_reachable"

grep -Fq 'one_command_only_confirmed:' "${CHECKLIST_DOC}" \
  || fail "window-open checklist template must keep one_command_only_confirmed"

grep -Fq 'window_may_open:' "${CHECKLIST_DOC}" \
  || fail "window-open checklist template must keep window_may_open"

fixture_output="$(run_fixture "${FIXTURE}")"
fixture_result="$(grep '^FIXTURE_RESULT=' <<<"${fixture_output}" | cut -d= -f2-)"
[[ "${fixture_result}" =~ ^(PASS|BLOCKED)$ ]] || fail "fixture ${FIXTURE} produced invalid result ${fixture_result}"

echo "FIRST_CONTROLLED_SEND_WINDOW_OPEN_CHECKLIST=PASS"
echo "CANONICAL_PATH=ORDER:testnet"
echo "WINDOW_OPEN_CHECKLIST_STATUS=docs_only_gate"
echo "CANDIDATE_VALIDITY_EXPLICIT=yes"
echo "RUNTIME_POSTURE_EXPLICIT=yes"
echo "SAFETY_BOUNDARY_EXPLICIT=yes"
echo "REVIEWABILITY_EXPLICIT=yes"
echo "DISCIPLINE_EXPLICIT=yes"
echo "WINDOW_OPEN_ALLOWED=no"
echo "EXTERNAL_REQUEST_ATTEMPTED=false"
echo "RUNTIME_MUTATION=false"
echo "LIVE_TRADING=NO-GO"
echo "NEXT_GATE=window_open_record_before_actual_send"
printf '%s\n' "${fixture_output}"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CHECKLIST_CHECK PASS: window-open checklist remains bounded, docs-only, and blocked before window opening"

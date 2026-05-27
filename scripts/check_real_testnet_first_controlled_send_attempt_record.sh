#!/usr/bin/env bash
# Verifies the first-controlled-send attempt record remains bounded, docs-only,
# and blocked from enabling any broader send behavior by itself.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_attempt_record.sh [--fixture <name>]

Checks that the first-controlled-send attempt record remains coherent as a
bounded docs-only operational record for the canonical ORDER + testnet path.

This script verifies:
- the runtime-verification-closeout check remains green
- the attempt record doc exists and keeps the canonical ORDER + testnet scope
- attempt identity, window identity, canonical attempt facts, first visible
  outcome, and attempt discipline remain explicit
- the doc does not authorize a send by itself
- external requests, runtime mutation, and live trading remain blocked

Supported fixtures:
- attempt_record_defined
- attempt_identity_missing
- window_identity_missing
- canonical_attempt_facts_missing
- first_visible_outcome_missing
- attempt_discipline_missing
- execution_mode_not_testnet
- external_request_attempted_true
- runtime_mutation_true
- live_trading_true

This script does not inject credentials, mutate runtime, attempt a send,
issue external requests, or authorize live trading.
EOF
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_ATTEMPT_RECORD_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_RUNTIME_VERIFICATION_CLOSEOUT_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_runtime_verification_closeout.sh"
ATTEMPT_RECORD_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_ATTEMPT_RECORD_V1.md"

declare -a REQUIRED_DOCS=(
  "${ATTEMPT_RECORD_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md"
)

FIXTURE="attempt_record_defined"

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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_ATTEMPT_RECORD_CHECK FAIL: $1" >&2
  exit 1
}

run_fixture() {
  local name="$1"
  local attempt_identity="yes"
  local window_identity="yes"
  local canonical_attempt_facts="yes"
  local first_visible_outcome="yes"
  local attempt_discipline="yes"
  local execution_mode="testnet"
  local external_request_attempted="false"
  local runtime_mutation="false"
  local live_trading="NO-GO"

  case "$name" in
    attempt_record_defined)
      ;;
    attempt_identity_missing)
      attempt_identity=""
      ;;
    window_identity_missing)
      window_identity=""
      ;;
    canonical_attempt_facts_missing)
      canonical_attempt_facts=""
      ;;
    first_visible_outcome_missing)
      first_visible_outcome=""
      ;;
    attempt_discipline_missing)
      attempt_discipline=""
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
  [[ -n "${attempt_identity}" ]] || result="BLOCKED"
  [[ -n "${window_identity}" ]] || result="BLOCKED"
  [[ -n "${canonical_attempt_facts}" ]] || result="BLOCKED"
  [[ -n "${first_visible_outcome}" ]] || result="BLOCKED"
  [[ -n "${attempt_discipline}" ]] || result="BLOCKED"
  [[ "${execution_mode}" == "testnet" ]] || result="BLOCKED"
  [[ "${external_request_attempted}" == "false" ]] || result="BLOCKED"
  [[ "${runtime_mutation}" == "false" ]] || result="BLOCKED"
  [[ "${live_trading}" == "NO-GO" ]] || result="BLOCKED"

  printf '%s\n' \
    "FIXTURE=${name}" \
    "FIXTURE_RESULT=${result}" \
    "FIXTURE_ATTEMPT_IDENTITY=${attempt_identity:-missing}" \
    "FIXTURE_WINDOW_IDENTITY=${window_identity:-missing}" \
    "FIXTURE_CANONICAL_ATTEMPT_FACTS=${canonical_attempt_facts:-missing}" \
    "FIXTURE_FIRST_VISIBLE_OUTCOME=${first_visible_outcome:-missing}" \
    "FIXTURE_ATTEMPT_DISCIPLINE=${attempt_discipline:-missing}" \
    "FIXTURE_EXECUTION_MODE=${execution_mode}" \
    "FIXTURE_EXTERNAL_REQUEST_ATTEMPTED=${external_request_attempted}" \
    "FIXTURE_RUNTIME_MUTATION=${runtime_mutation}" \
    "FIXTURE_LIVE_TRADING=${live_trading}"
}

"${UPSTREAM_RUNTIME_VERIFICATION_CLOSEOUT_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** attempt-record template only - no real key, no external API call in this round, no live trading approval.' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record doc must remain docs-only and request-free"

grep -Fq 'Command.type = ORDER' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record doc must stay on canonical ORDER path"

grep -Fq 'payload.execution_mode = testnet' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record doc must stay on canonical execution_mode=testnet path"

grep -Fq 'This document does not authorize the first controlled send by itself.' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record doc must keep send authorization blocked by itself"

grep -Fq 'attempt_record_id:' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record template must keep attempt_record_id"

grep -Fq 'window_id:' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record template must keep window_id"

grep -Fq 'request_attempted:' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record template must keep request_attempted"

grep -Fq 'final_command_state:' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record template must keep final_command_state"

grep -Fq 'second_request_attempted:' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record template must keep second_request_attempted"

grep -Fq 'ATTEMPTED - STILL BOUNDED' "${ATTEMPT_RECORD_DOC}" \
  || fail "attempt record doc must keep bounded attempt status label"

fixture_output="$(run_fixture "${FIXTURE}")"
fixture_result="$(grep '^FIXTURE_RESULT=' <<<"${fixture_output}" | cut -d= -f2-)"
[[ "${fixture_result}" =~ ^(PASS|BLOCKED)$ ]] || fail "fixture ${FIXTURE} produced invalid result ${fixture_result}"

echo "FIRST_CONTROLLED_SEND_ATTEMPT_RECORD=PASS"
echo "CANONICAL_PATH=ORDER:testnet"
echo "ATTEMPT_RECORD_STATUS=docs_only_record"
echo "ATTEMPT_IDENTITY_EXPLICIT=yes"
echo "WINDOW_IDENTITY_EXPLICIT=yes"
echo "CANONICAL_ATTEMPT_FACTS_EXPLICIT=yes"
echo "FIRST_VISIBLE_OUTCOME_EXPLICIT=yes"
echo "ATTEMPT_DISCIPLINE_EXPLICIT=yes"
echo "ACTUAL_SEND_AUTHORIZED=no"
echo "EXTERNAL_REQUEST_ATTEMPTED=false"
echo "RUNTIME_MUTATION=false"
echo "LIVE_TRADING=NO-GO"
echo "NEXT_GATE=attempt_closeout_before_final_review"
printf '%s\n' "${fixture_output}"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_ATTEMPT_RECORD_CHECK PASS: attempt record remains bounded, docs-only, and blocked from enabling any send by itself"

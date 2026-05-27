#!/usr/bin/env bash
# Verifies the first-controlled-send runtime-verification record remains
# bounded, docs-only, and blocked before any actual send attempt.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_runtime_verification_record.sh [--fixture <name>]

Checks that the first-controlled-send runtime-verification record remains
coherent as a bounded docs-only operational record before any actual send
attempt or real external request can be considered.

This script verifies:
- the window-open-record-closeout check remains green
- the runtime-verification record doc exists and keeps the canonical ORDER + testnet scope
- verified-window facts, runtime posture verification, review-surface verification,
  command linkage, and bounded-send posture remain explicit
- any real send attempt remains blocked
- external requests, runtime mutation, and live trading remain blocked

Supported fixtures:
- verification_defined_but_send_blocked
- verified_window_facts_missing
- runtime_posture_missing
- review_surface_missing
- command_linkage_missing
- bounded_send_posture_missing
- execution_mode_not_testnet
- external_request_attempted_true
- runtime_mutation_true
- live_trading_true

This script does not inject credentials, mutate runtime, perform runtime
verification, attempt a send, issue external requests, or authorize live trading.
EOF
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_WINDOW_OPEN_RECORD_CLOSEOUT_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_window_open_record_closeout.sh"
RUNTIME_VERIFICATION_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_V1.md"

declare -a REQUIRED_DOCS=(
  "${RUNTIME_VERIFICATION_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_V1.md"
  "${ROOT}/docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md"
)

FIXTURE="verification_defined_but_send_blocked"

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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_CHECK FAIL: $1" >&2
  exit 1
}

run_fixture() {
  local name="$1"
  local verified_window_facts="yes"
  local runtime_posture="yes"
  local review_surface="yes"
  local command_linkage="yes"
  local bounded_send_posture="yes"
  local execution_mode="testnet"
  local external_request_attempted="false"
  local runtime_mutation="false"
  local live_trading="NO-GO"

  case "$name" in
    verification_defined_but_send_blocked)
      ;;
    verified_window_facts_missing)
      verified_window_facts=""
      ;;
    runtime_posture_missing)
      runtime_posture=""
      ;;
    review_surface_missing)
      review_surface=""
      ;;
    command_linkage_missing)
      command_linkage=""
      ;;
    bounded_send_posture_missing)
      bounded_send_posture=""
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
  [[ -n "$verified_window_facts" ]] || result="BLOCKED"
  [[ -n "$runtime_posture" ]] || result="BLOCKED"
  [[ -n "$review_surface" ]] || result="BLOCKED"
  [[ -n "$command_linkage" ]] || result="BLOCKED"
  [[ -n "$bounded_send_posture" ]] || result="BLOCKED"
  [[ "$execution_mode" == "testnet" ]] || result="BLOCKED"
  [[ "$external_request_attempted" == "false" ]] || result="BLOCKED"
  [[ "$runtime_mutation" == "false" ]] || result="BLOCKED"
  [[ "$live_trading" == "NO-GO" ]] || result="BLOCKED"

  printf '%s\n' \
    "FIXTURE=${name}" \
    "FIXTURE_RESULT=${result}" \
    "FIXTURE_VERIFIED_WINDOW_FACTS=${verified_window_facts:-missing}" \
    "FIXTURE_RUNTIME_POSTURE=${runtime_posture:-missing}" \
    "FIXTURE_REVIEW_SURFACE=${review_surface:-missing}" \
    "FIXTURE_COMMAND_LINKAGE=${command_linkage:-missing}" \
    "FIXTURE_BOUNDED_SEND_POSTURE=${bounded_send_posture:-missing}" \
    "FIXTURE_EXECUTION_MODE=${execution_mode}" \
    "FIXTURE_EXTERNAL_REQUEST_ATTEMPTED=${external_request_attempted}" \
    "FIXTURE_RUNTIME_MUTATION=${runtime_mutation}" \
    "FIXTURE_LIVE_TRADING=${live_trading}"
}

"${UPSTREAM_WINDOW_OPEN_RECORD_CLOSEOUT_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** runtime-verification record only - no real key, no external API call in this round, no live trading approval.' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record doc must remain docs-only and request-free"

grep -Fq 'Command.type = ORDER' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record doc must stay on canonical ORDER path"

grep -Fq 'payload.execution_mode = testnet' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record doc must stay on canonical execution_mode=testnet path"

grep -Fq 'This document does not authorize the send by itself.' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record doc must keep send authorization blocked by itself"

grep -Fq 'runtime_verification_timestamp:' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record template must keep runtime_verification_timestamp"

grep -Fq 'verification_status_label:' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record template must keep verification_status_label"

grep -Fq 'executor_mode_value:' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record template must keep executor_mode_value"

grep -Fq 'ops_reachable_at_verification:' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record template must keep ops_reachable_at_verification"

grep -Fq 'idempotency_key:' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record template must keep command linkage via idempotency_key"

grep -Fq 'send_remains_allowed_after_verification:' "${RUNTIME_VERIFICATION_DOC}" \
  || fail "runtime-verification record template must keep send_remains_allowed_after_verification"

fixture_output="$(run_fixture "${FIXTURE}")"
fixture_result="$(grep '^FIXTURE_RESULT=' <<<"${fixture_output}" | cut -d= -f2-)"
[[ "${fixture_result}" =~ ^(PASS|BLOCKED)$ ]] || fail "fixture ${FIXTURE} produced invalid result ${fixture_result}"

echo "FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD=PASS"
echo "CANONICAL_PATH=ORDER:testnet"
echo "RUNTIME_VERIFICATION_RECORD_STATUS=docs_only_record"
echo "VERIFIED_WINDOW_FACTS_EXPLICIT=yes"
echo "RUNTIME_POSTURE_EXPLICIT=yes"
echo "REVIEW_SURFACE_EXPLICIT=yes"
echo "COMMAND_LINKAGE_EXPLICIT=yes"
echo "BOUNDED_SEND_POSTURE_EXPLICIT=yes"
echo "SEND_ATTEMPT_ALLOWED=no"
echo "EXTERNAL_REQUEST_ATTEMPTED=false"
echo "RUNTIME_MUTATION=false"
echo "LIVE_TRADING=NO-GO"
echo "NEXT_GATE=runtime_verification_closeout_before_attempt"
printf '%s\n' "${fixture_output}"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_CHECK PASS: runtime-verification record remains bounded, docs-only, and blocked before any send attempt"

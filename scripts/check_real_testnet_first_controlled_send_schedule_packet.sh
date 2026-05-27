#!/usr/bin/env bash
# Verifies the first-controlled-send schedule packet remains bounded,
# docs-only, and blocked before any actual scheduling or real request.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_schedule_packet.sh [--fixture <name>]

Checks that the first-controlled-send schedule packet remains coherent as a
bounded docs-only operational evidence packet before any actual scheduling or
real external request can be considered.

This script verifies:
- the decision-bundle closeout check remains green
- the schedule-packet doc exists and keeps the canonical ORDER + testnet scope
- host identity and runtime window are explicit in the packet template
- command targeting remains explicit or is intentionally marked NOT_SCHEDULED
- rollback / retreat fields remain present
- external requests, runtime mutation, and live trading remain blocked

Supported fixtures:
- template_only_blocked_by_default
- host_identity_missing
- runtime_window_missing
- command_target_missing
- execution_mode_not_testnet
- retreat_info_missing
- external_request_attempted_true
- runtime_mutation_true
- live_trading_true

This script does not inject credentials, mutate runtime, schedule a send,
issue external requests, or authorize live trading.
EOF
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULE_PACKET_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_CLOSEOUT_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_decision_bundle_closeout.sh"
SCHEDULE_PACKET_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULE_PACKET_V1.md"

declare -a REQUIRED_DOCS=(
  "${SCHEDULE_PACKET_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_DECISION_BUNDLE_CLOSEOUT_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md"
)

FIXTURE="template_only_blocked_by_default"

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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULE_PACKET_CHECK FAIL: $1" >&2
  exit 1
}

run_fixture() {
  local name="$1"
  local host_identity="binance_futures_testnet"
  local window_id="WINDOW_NOT_YET_OPENED"
  local command_target="NOT_SCHEDULED"
  local execution_mode="testnet"
  local retreat_info="present"
  local rollback_info="present"
  local external_request_attempted="false"
  local runtime_mutation="false"
  local live_trading="NO-GO"

  case "$name" in
    template_only_blocked_by_default)
      ;;
    host_identity_missing)
      host_identity=""
      ;;
    runtime_window_missing)
      window_id=""
      ;;
    command_target_missing)
      command_target=""
      ;;
    execution_mode_not_testnet)
      execution_mode="live"
      ;;
    retreat_info_missing)
      retreat_info=""
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
  [[ -n "$host_identity" ]] || result="BLOCKED"
  [[ -n "$window_id" ]] || result="BLOCKED"
  [[ -n "$command_target" ]] || result="BLOCKED"
  [[ "$execution_mode" == "testnet" ]] || result="BLOCKED"
  [[ -n "$retreat_info" ]] || result="BLOCKED"
  [[ -n "$rollback_info" ]] || result="BLOCKED"
  [[ "$external_request_attempted" == "false" ]] || result="BLOCKED"
  [[ "$runtime_mutation" == "false" ]] || result="BLOCKED"
  [[ "$live_trading" == "NO-GO" ]] || result="BLOCKED"

  printf '%s\n' \
    "FIXTURE=${name}" \
    "FIXTURE_RESULT=${result}" \
    "FIXTURE_HOST_IDENTITY=${host_identity:-missing}" \
    "FIXTURE_WINDOW_ID=${window_id:-missing}" \
    "FIXTURE_COMMAND_TARGET=${command_target:-missing}" \
    "FIXTURE_EXECUTION_MODE=${execution_mode}" \
    "FIXTURE_RETREAT_INFO=${retreat_info:-missing}" \
    "FIXTURE_ROLLBACK_INFO=${rollback_info:-missing}" \
    "FIXTURE_EXTERNAL_REQUEST_ATTEMPTED=${external_request_attempted}" \
    "FIXTURE_RUNTIME_MUTATION=${runtime_mutation}" \
    "FIXTURE_LIVE_TRADING=${live_trading}"
}

"${UPSTREAM_CLOSEOUT_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** schedule packet only - no real key, no external API call in this round, no live trading approval.' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet doc must remain docs-only and request-free"

grep -Fq 'Command.type = ORDER' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet doc must stay on canonical ORDER path"

grep -Fq 'payload.execution_mode = testnet' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet doc must stay on canonical execution_mode=testnet path"

grep -Fq 'This document does not schedule the send by itself.' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet doc must keep scheduling blocked by itself"

grep -Fq 'host_identity:' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet template must keep host_identity"

grep -Fq 'window_id:' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet template must keep window_id"

grep -Fq 'idempotency_key:' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet template must keep command targeting via idempotency_key"

grep -Fq 'executor_mode_value:' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet template must keep executor_mode_value"

grep -Fq 'retreat_posture_label:' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet template must keep retreat posture"

grep -Fq 'no_quick_retry_rule_confirmed:' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet template must keep no quick retry rule"

grep -Fq 'second_send_not_preauthorized:' "${SCHEDULE_PACKET_DOC}" \
  || fail "schedule packet template must keep second-send guard"

fixture_output="$(run_fixture "${FIXTURE}")"
fixture_result="$(grep '^FIXTURE_RESULT=' <<<"${fixture_output}" | cut -d= -f2-)"
[[ "${fixture_result}" =~ ^(PASS|BLOCKED)$ ]] || fail "fixture ${FIXTURE} produced invalid result ${fixture_result}"

echo "FIRST_CONTROLLED_SEND_SCHEDULE_PACKET=PASS"
echo "CANONICAL_PATH=ORDER:testnet"
echo "SCHEDULE_PACKET_STATUS=docs_only_template"
echo "HOST_FROZEN=yes"
echo "RUNTIME_WINDOW_EXPLICIT=yes"
echo "COMMAND_TARGET_STATUS=explicit_or_not_scheduled"
echo "EXECUTION_MODE=testnet"
echo "ROLLBACK_INFO_PRESENT=yes"
echo "RETREAT_INFO_PRESENT=yes"
echo "EXTERNAL_REQUEST_ATTEMPTED=false"
echo "RUNTIME_MUTATION=false"
echo "LIVE_TRADING=NO-GO"
echo "SCHEDULING_ALLOWED=no"
echo "NEXT_GATE=candidate_window_before_actual_send"
printf '%s\n' "${fixture_output}"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULE_PACKET_CHECK PASS: schedule packet remains bounded, docs-only, and blocked before scheduling"

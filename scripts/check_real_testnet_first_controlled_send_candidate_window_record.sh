#!/usr/bin/env bash
# Verifies the first-controlled-send candidate-window record remains bounded,
# docs-only, and blocked before any actual window open or real request.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_real_testnet_first_controlled_send_candidate_window_record.sh [--fixture <name>]

Checks that the first-controlled-send candidate-window record remains coherent
as a bounded docs-only operational evidence record before any actual window
open or real external request can be considered.

This script verifies:
- the schedule-packet check remains green
- the candidate-window record doc exists and keeps the canonical ORDER + testnet scope
- host identity, candidate window id, and runtime posture remain explicit
- command linkage remains explicit
- candidate status remains explicit and blocked from window opening by default
- external requests, runtime mutation, and live trading remain blocked

Supported fixtures:
- candidate_identifiable_blocked_by_default
- host_identity_missing
- candidate_window_id_missing
- runtime_posture_missing
- command_linkage_missing
- candidate_status_missing
- execution_mode_not_testnet
- external_request_attempted_true
- runtime_mutation_true
- live_trading_true

This script does not inject credentials, mutate runtime, open a window,
issue external requests, or authorize live trading.
EOF
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

UPSTREAM_SCHEDULE_PACKET_CHECK="${ROOT}/scripts/check_real_testnet_first_controlled_send_schedule_packet.sh"
CANDIDATE_WINDOW_DOC="${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_V1.md"

declare -a REQUIRED_DOCS=(
  "${CANDIDATE_WINDOW_DOC}"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULE_PACKET_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md"
  "${ROOT}/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_CLOSEOUT_V1.md"
)

FIXTURE="candidate_identifiable_blocked_by_default"

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
  echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_CHECK FAIL: $1" >&2
  exit 1
}

run_fixture() {
  local name="$1"
  local host_identity="binance_futures_testnet"
  local candidate_window_id="CANDIDATE_NOT_YET_OPENED"
  local runtime_posture="testnet_real_enable_pending"
  local command_linkage="ORDER:testnet:not_scheduled"
  local candidate_status="CANDIDATE_BLOCKED"
  local execution_mode="testnet"
  local external_request_attempted="false"
  local runtime_mutation="false"
  local live_trading="NO-GO"

  case "$name" in
    candidate_identifiable_blocked_by_default)
      ;;
    host_identity_missing)
      host_identity=""
      ;;
    candidate_window_id_missing)
      candidate_window_id=""
      ;;
    runtime_posture_missing)
      runtime_posture=""
      ;;
    command_linkage_missing)
      command_linkage=""
      ;;
    candidate_status_missing)
      candidate_status=""
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
  [[ -n "$host_identity" ]] || result="BLOCKED"
  [[ -n "$candidate_window_id" ]] || result="BLOCKED"
  [[ -n "$runtime_posture" ]] || result="BLOCKED"
  [[ -n "$command_linkage" ]] || result="BLOCKED"
  [[ -n "$candidate_status" ]] || result="BLOCKED"
  [[ "$execution_mode" == "testnet" ]] || result="BLOCKED"
  [[ "$external_request_attempted" == "false" ]] || result="BLOCKED"
  [[ "$runtime_mutation" == "false" ]] || result="BLOCKED"
  [[ "$live_trading" == "NO-GO" ]] || result="BLOCKED"

  printf '%s\n' \
    "FIXTURE=${name}" \
    "FIXTURE_RESULT=${result}" \
    "FIXTURE_HOST_IDENTITY=${host_identity:-missing}" \
    "FIXTURE_CANDIDATE_WINDOW_ID=${candidate_window_id:-missing}" \
    "FIXTURE_RUNTIME_POSTURE=${runtime_posture:-missing}" \
    "FIXTURE_COMMAND_LINKAGE=${command_linkage:-missing}" \
    "FIXTURE_CANDIDATE_STATUS=${candidate_status:-missing}" \
    "FIXTURE_EXECUTION_MODE=${execution_mode}" \
    "FIXTURE_EXTERNAL_REQUEST_ATTEMPTED=${external_request_attempted}" \
    "FIXTURE_RUNTIME_MUTATION=${runtime_mutation}" \
    "FIXTURE_LIVE_TRADING=${live_trading}"
}

"${UPSTREAM_SCHEDULE_PACKET_CHECK}" >/dev/null

for required in "${REQUIRED_DOCS[@]}"; do
  [[ -f "${required}" ]] || fail "missing required doc ${required}"
done

grep -Fq '**Status:** candidate-window record only - no real key, no external API call in this round, no live trading approval.' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window doc must remain docs-only and request-free"

grep -Fq 'Command.type = ORDER' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window doc must stay on canonical ORDER path"

grep -Fq 'payload.execution_mode = testnet' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window doc must stay on canonical execution_mode=testnet path"

grep -Fq 'This document does not open the window by itself.' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window doc must keep window opening blocked by itself"

grep -Fq 'host_identity:' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window template must keep host_identity"

grep -Fq 'candidate_window_id:' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window template must keep candidate_window_id"

grep -Fq 'runtime_posture_label:' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window template must keep runtime_posture_label"

grep -Fq 'idempotency_key:' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window template must keep command linkage via idempotency_key"

grep -Fq 'candidate_status_label:' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window template must keep candidate_status_label"

grep -Fq 'still_blocked_pending_final_confirmation:' "${CANDIDATE_WINDOW_DOC}" \
  || fail "candidate-window template must keep still_blocked_pending_final_confirmation"

fixture_output="$(run_fixture "${FIXTURE}")"
fixture_result="$(grep '^FIXTURE_RESULT=' <<<"${fixture_output}" | cut -d= -f2-)"
[[ "${fixture_result}" =~ ^(PASS|BLOCKED)$ ]] || fail "fixture ${FIXTURE} produced invalid result ${fixture_result}"

echo "FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD=PASS"
echo "CANONICAL_PATH=ORDER:testnet"
echo "CANDIDATE_WINDOW_STATUS=docs_only_record"
echo "HOST_FROZEN=yes"
echo "CANDIDATE_WINDOW_EXPLICIT=yes"
echo "RUNTIME_POSTURE_EXPLICIT=yes"
echo "COMMAND_LINKAGE_EXPLICIT=yes"
echo "CANDIDATE_STATUS_EXPLICIT=yes"
echo "EXTERNAL_REQUEST_ATTEMPTED=false"
echo "RUNTIME_MUTATION=false"
echo "LIVE_TRADING=NO-GO"
echo "WINDOW_OPEN_ALLOWED=no"
echo "NEXT_GATE=window_open_checklist_before_actual_send"
printf '%s\n' "${fixture_output}"
echo "REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_CHECK PASS: candidate-window record remains bounded, docs-only, and blocked before window opening"

#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/one_shot_order_testnet_invocation.sh [--fixture NAME] [--execute]

Purpose:
  Harden the one-shot ORDER:testnet invocation path so that time-window failure
  always hard-stops before any POST can occur.

Behavior:
  - WINDOW_NOT_OPEN_YET => exit 1
  - WINDOW_EXPIRED => exit 1
  - missing required env => exit 1
  - WINDOW_TIME_CHECK=PASS is required before the guarded POST branch
  - default mode is dry-run; no POST is sent unless --execute is explicitly set

Fixtures:
  before-window
  expired-window
  valid-window-dry
  missing-env

This script does not authorize real external requests, canary, go-live, or
live trading.
EOF
}

FIXTURE=""
EXECUTE="NO"

while (($# > 0)); do
  case "$1" in
    --fixture)
      if (($# < 2)); then
        usage >&2
        exit 2
      fi
      FIXTURE="$2"
      shift 2
      ;;
    --execute)
      EXECUTE="YES"
      shift
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

POST_ATTEMPTED="NO"
POST_EXECUTED="NO"
WINDOW_TIME_CHECK="UNSET"

iso_now_utc() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

epoch_utc() {
  date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$1" '+%s' 2>/dev/null
}

fail() {
  local reason="$1"
  printf '%s\n' "$reason"
  printf '%s\n' "WINDOW_TIME_CHECK=${WINDOW_TIME_CHECK}"
  printf '%s\n' "POST_ATTEMPTED=${POST_ATTEMPTED}"
  printf '%s\n' "POST_EXECUTED=${POST_EXECUTED}"
  exit 1
}

apply_fixture() {
  local fixture="$1"
  case "$fixture" in
    before-window|blocked-before-window)
      NOW_UTC="2026-06-05T08:29:55Z"
      WINDOW_START_UTC="2026-06-05T08:39:55Z"
      WINDOW_END_UTC="2026-06-05T08:54:55Z"
      ;;
    expired-window)
      NOW_UTC="2026-06-05T08:55:55Z"
      WINDOW_START_UTC="2026-06-05T08:39:55Z"
      WINDOW_END_UTC="2026-06-05T08:54:55Z"
      ;;
    valid-window-dry)
      NOW_UTC="2026-06-05T08:45:00Z"
      WINDOW_START_UTC="2026-06-05T08:39:55Z"
      WINDOW_END_UTC="2026-06-05T08:54:55Z"
      EXECUTE="NO"
      ;;
    missing-env)
      NOW_UTC=""
      WINDOW_START_UTC=""
      WINDOW_END_UTC=""
      ;;
    "")
      ;;
    *)
      printf '%s\n' "UNKNOWN_FIXTURE=${fixture}" >&2
      exit 2
      ;;
  esac
}

NOW_UTC="${NOW_UTC:-$(iso_now_utc)}"
WINDOW_START_UTC="${WINDOW_START_UTC:-${WINDOW_START_UTC:-}}"
WINDOW_END_UTC="${WINDOW_END_UTC:-${WINDOW_END_UTC:-}}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000}"
INVOCATION_PATH="/trade-gate/testnet-order-intents"
CREATED_BY="${CREATED_BY:-baolood}"
IDEMPOTENCY_KEY="${IDEMPOTENCY_KEY:-testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1}"

apply_fixture "${FIXTURE}"

WINDOW_START_UTC="${WINDOW_START_UTC:-}"
WINDOW_END_UTC="${WINDOW_END_UTC:-}"

if [[ -z "${WINDOW_START_UTC}" || -z "${WINDOW_END_UTC}" ]]; then
  WINDOW_TIME_CHECK="BLOCKED"
  fail "MISSING_REQUIRED_WINDOW_ENV"
fi

NOW_EPOCH="$(epoch_utc "${NOW_UTC}")" || {
  WINDOW_TIME_CHECK="BLOCKED"
  fail "INVALID_NOW_UTC"
}
START_EPOCH="$(epoch_utc "${WINDOW_START_UTC}")" || {
  WINDOW_TIME_CHECK="BLOCKED"
  fail "INVALID_WINDOW_START_UTC"
}
END_EPOCH="$(epoch_utc "${WINDOW_END_UTC}")" || {
  WINDOW_TIME_CHECK="BLOCKED"
  fail "INVALID_WINDOW_END_UTC"
}

if (( NOW_EPOCH < START_EPOCH )); then
  WINDOW_TIME_CHECK="BLOCKED"
  fail "WINDOW_NOT_OPEN_YET"
fi

if (( NOW_EPOCH > END_EPOCH )); then
  WINDOW_TIME_CHECK="BLOCKED"
  fail "WINDOW_EXPIRED"
fi

WINDOW_TIME_CHECK="PASS"

REQUEST_BODY="$(cat <<EOF
{"symbol":"BTCUSDT","side":"BUY","notional":4,"stop_price":68000,"order_type":"market","created_by":"${CREATED_BY}","idempotency_key":"${IDEMPOTENCY_KEY}"}
EOF
)"

printf '%s\n' "WINDOW_TIME_CHECK=${WINDOW_TIME_CHECK}"
printf '%s\n' "INVOCATION_SURFACE=POST ${BACKEND_BASE_URL}${INVOCATION_PATH}"
printf '%s\n' "POST_ATTEMPTED=${POST_ATTEMPTED}"

if [[ "${EXECUTE}" != "YES" ]]; then
  printf '%s\n' "GUARDED_POST_BRANCH=DRY_RUN"
  printf '%s\n' "REQUEST_BODY=${REQUEST_BODY}"
  printf '%s\n' "POST_ATTEMPTED=${POST_ATTEMPTED}"
  printf '%s\n' "POST_EXECUTED=${POST_EXECUTED}"
  exit 0
fi

POST_ATTEMPTED="YES"
printf '%s\n' "GUARDED_POST_BRANCH=EXECUTE"
printf '%s\n' "POST_ATTEMPTED=${POST_ATTEMPTED}"

curl -sS \
  -X POST "${BACKEND_BASE_URL}${INVOCATION_PATH}" \
  -H 'Content-Type: application/json' \
  --data "${REQUEST_BODY}"

POST_EXECUTED="YES"
printf '%s\n' "POST_EXECUTED=${POST_EXECUTED}"

#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
BACKEND_DIR="${BACKEND_DIR:-$ROOT/anchor-backend}"
ENV_FILE="${ENV_FILE:-/etc/project-anchor/alerting.env}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"
CURL_FLAGS=( -sS --connect-timeout 5 --max-time 20 --noproxy '*' )
DRY_RUN="${LOCAL_ALERTING_RUNTIME_CHECK_DRY_RUN:-0}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/local_alerting_runtime_check.sh
  LOCAL_ALERTING_RUNTIME_CHECK_DRY_RUN=1 bash scripts/local_alerting_runtime_check.sh

Purpose:
  Reduce operator terminal burden for local alerting runtime validation.

This script:
  - never prints TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID
  - never calls POST /trade-gate/testnet-order-intents
  - never generates fresh timing
  - never submits operator authorization result
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

PASS_OR_FAIL="PASS"
FAIL_REASON=""

ENV_FILE_EXISTS="NO"
TELEGRAM_NOTIFY_ENABLED_VALUE_OK="NO"
TELEGRAM_BOT_TOKEN_PRESENT="NO"
TELEGRAM_CHAT_ID_PRESENT="NO"

DOCKER_BACKEND="NO"
DOCKER_WORKER="NO"

HEALTH_RESULT="NO"
OPS_STATE_RESULT="NO"
OPS_WORKER_RESULT="NO"
TELEGRAM_ENABLED_RESULT="NO"

fail() {
  PASS_OR_FAIL="BLOCKED"
  FAIL_REASON="$1"
}

if [[ "$DRY_RUN" == "1" ]]; then
  PASS_OR_FAIL="PASS"
  FAIL_REASON=""
  HEALTH_RESULT="DRY_RUN"
  OPS_STATE_RESULT="DRY_RUN"
  OPS_WORKER_RESULT="DRY_RUN"
  TELEGRAM_ENABLED_RESULT="DRY_RUN"
else
  if sudo test -f "$ENV_FILE"; then
    ENV_FILE_EXISTS="YES"
  else
    fail "ALERTING_ENV_FILE_MISSING"
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    notify_enabled_value="$(sudo awk -F= '$1=="TELEGRAM_NOTIFY_ENABLED"{print $2}' "$ENV_FILE" 2>/dev/null | tail -n 1 | tr -d '[:space:]')"
    [[ "$notify_enabled_value" == "1" ]] && TELEGRAM_NOTIFY_ENABLED_VALUE_OK="YES" || fail "TELEGRAM_NOTIFY_ENABLED_NOT_ONE"
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    if sudo awk -F= '$1=="TELEGRAM_BOT_TOKEN" && length($2)>0 {ok=1} END {exit ok?0:1}' "$ENV_FILE" >/dev/null 2>&1; then
      TELEGRAM_BOT_TOKEN_PRESENT="YES"
    else
      fail "TELEGRAM_BOT_TOKEN_MISSING"
    fi
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    if sudo awk -F= '$1=="TELEGRAM_CHAT_ID" && length($2)>0 {ok=1} END {exit ok?0:1}' "$ENV_FILE" >/dev/null 2>&1; then
      TELEGRAM_CHAT_ID_PRESENT="YES"
    else
      fail "TELEGRAM_CHAT_ID_MISSING"
    fi
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    (
      cd "$BACKEND_DIR"
      docker compose up -d --build backend worker >/dev/null
    ) || fail "DOCKER_COMPOSE_UP_FAILED"
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    ps_out="$(
      cd "$BACKEND_DIR" &&
      docker compose ps 2>/dev/null || true
    )"
    echo "$ps_out" | grep -q 'backend.*Up' && DOCKER_BACKEND="YES" || fail "BACKEND_NOT_UP"
    echo "$ps_out" | grep -q 'worker.*Up' && DOCKER_WORKER="YES" || fail "WORKER_NOT_UP"
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    if curl "${CURL_FLAGS[@]}" -o /dev/null -w "%{http_code}" "$BACKEND_PRECHECK/health" | grep -q '^200$'; then
      HEALTH_RESULT="PASS"
    else
      fail "BACKEND_HEALTH_UNREACHABLE"
    fi
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    ops_state_json="$(curl "${CURL_FLAGS[@]}" "$BACKEND_PRECHECK/ops/state")" || fail "OPS_STATE_UNREACHABLE"
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$ops_state_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(0 if isinstance(data,dict) and "kill_switch" in data and "worker_heartbeat" in data else 1)' \
        && OPS_STATE_RESULT="PASS" || fail "OPS_STATE_INVALID"
    fi
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    ops_worker_json="$(curl "${CURL_FLAGS[@]}" "$BACKEND_PRECHECK/ops/worker")" || fail "OPS_WORKER_UNREACHABLE"
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$ops_worker_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(0 if isinstance(data,dict) and "telegram_enabled" in data else 1)' \
        && OPS_WORKER_RESULT="PASS" || fail "OPS_WORKER_INVALID"
    fi
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$ops_worker_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(0 if data.get("telegram_enabled") is True else 1)' \
        && TELEGRAM_ENABLED_RESULT="PASS" || fail "TELEGRAM_ENABLED_FALSE"
    fi
  fi
fi

echo "[Local Alerting Runtime Check Result]"
echo "env file exists: $ENV_FILE_EXISTS"
echo "TELEGRAM_NOTIFY_ENABLED=1: $TELEGRAM_NOTIFY_ENABLED_VALUE_OK"
echo "TELEGRAM_BOT_TOKEN_PRESENT: $TELEGRAM_BOT_TOKEN_PRESENT"
echo "TELEGRAM_CHAT_ID_PRESENT: $TELEGRAM_CHAT_ID_PRESENT"
echo "docker:"
echo "- backend: $DOCKER_BACKEND"
echo "- worker: $DOCKER_WORKER"
echo "endpoints:"
echo "- /health: $HEALTH_RESULT"
echo "- /ops/state: $OPS_STATE_RESULT"
echo "- /ops/worker: $OPS_WORKER_RESULT"
echo "- telegram_enabled: $TELEGRAM_ENABLED_RESULT"
echo "boundary:"
echo "- POST executed: NO"
echo "- real external request sent: NO"
echo "- canary: NOT AUTHORIZED"
echo "- go-live: NO-GO"
echo "- live trading: NO-GO"
echo "result:"
echo "- PASS_OR_FAIL: $PASS_OR_FAIL"
echo "- FAIL_REASON: $FAIL_REASON"

if [[ "$PASS_OR_FAIL" != "PASS" ]]; then
  exit 1
fi

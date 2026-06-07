#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
BACKEND_DIR="${BACKEND_DIR:-$ROOT/anchor-backend}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"
CURL_FLAGS=( -sS --connect-timeout 5 --max-time 20 --noproxy '*' )
DRY_RUN="${LOCAL_TESTNET_RUNTIME_CHECK_DRY_RUN:-0}"
HTTP_RETRY_COUNT="${LOCAL_TESTNET_RUNTIME_CHECK_HTTP_RETRY_COUNT:-12}"
HTTP_RETRY_SLEEP_SECONDS="${LOCAL_TESTNET_RUNTIME_CHECK_HTTP_RETRY_SLEEP_SECONDS:-2}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/local_testnet_runtime_check.sh
  LOCAL_TESTNET_RUNTIME_CHECK_DRY_RUN=1 bash scripts/local_testnet_runtime_check.sh

Purpose:
  Reduce operator terminal burden for canonical testnet runtime validation.

This script:
  - never prints TESTNET_EXCHANGE_API_KEY or TESTNET_EXCHANGE_API_SECRET
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

DOCKER_BACKEND="NO"
DOCKER_WORKER="NO"

TESTNET_EXCHANGE_BASE_URL_PRESENT="NO"
TESTNET_EXCHANGE_API_KEY_PRESENT="NO"
TESTNET_EXCHANGE_API_SECRET_PRESENT="NO"
TESTNET_EXCHANGE_KEY_ID_PRESENT="NO"
TESTNET_EXECUTOR_MODE_REAL="NO"
TESTNET_EXECUTOR_REAL_ENABLE_ONE="NO"

HEALTH_RESULT="NO"
OPS_STATE_RESULT="NO"
OPS_WORKER_RESULT="NO"
KILL_SWITCH_RESULT="NO"
WORKER_HEARTBEAT_RESULT="NO"
TELEGRAM_ENABLED_RESULT="NO"

fail() {
  PASS_OR_FAIL="BLOCKED"
  FAIL_REASON="$1"
}

curl_json_with_retry() {
  local endpoint="$1"
  local attempt=1
  local output=""
  while (( attempt <= HTTP_RETRY_COUNT )); do
    if output="$(curl "${CURL_FLAGS[@]}" "$BACKEND_PRECHECK$endpoint" 2>/dev/null)"; then
      printf '%s' "$output"
      return 0
    fi
    sleep "$HTTP_RETRY_SLEEP_SECONDS"
    ((attempt+=1))
  done
  return 1
}

curl_health_with_retry() {
  local attempt=1
  local code=""
  while (( attempt <= HTTP_RETRY_COUNT )); do
    if code="$(curl "${CURL_FLAGS[@]}" -o /dev/null -w "%{http_code}" "$BACKEND_PRECHECK/health" 2>/dev/null)" && [[ "$code" == "200" ]]; then
      return 0
    fi
    sleep "$HTTP_RETRY_SLEEP_SECONDS"
    ((attempt+=1))
  done
  return 1
}

if [[ "$DRY_RUN" == "1" ]]; then
  HEALTH_RESULT="DRY_RUN"
  OPS_STATE_RESULT="DRY_RUN"
  OPS_WORKER_RESULT="DRY_RUN"
  KILL_SWITCH_RESULT="DRY_RUN"
  WORKER_HEARTBEAT_RESULT="DRY_RUN"
  TELEGRAM_ENABLED_RESULT="DRY_RUN"
  TESTNET_EXCHANGE_BASE_URL_PRESENT="DRY_RUN"
  TESTNET_EXCHANGE_API_KEY_PRESENT="DRY_RUN"
  TESTNET_EXCHANGE_API_SECRET_PRESENT="DRY_RUN"
  TESTNET_EXCHANGE_KEY_ID_PRESENT="DRY_RUN"
  TESTNET_EXECUTOR_MODE_REAL="DRY_RUN"
  TESTNET_EXECUTOR_REAL_ENABLE_ONE="DRY_RUN"
  DOCKER_BACKEND="DRY_RUN"
  DOCKER_WORKER="DRY_RUN"
else
  (
    cd "$BACKEND_DIR"
    docker compose up -d --build backend worker >/dev/null
  ) || fail "DOCKER_COMPOSE_UP_FAILED"

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    ps_out="$(
      cd "$BACKEND_DIR" &&
      docker compose ps 2>/dev/null || true
    )"
    echo "$ps_out" | grep -q 'backend.*Up' && DOCKER_BACKEND="YES" || fail "BACKEND_NOT_UP"
    echo "$ps_out" | grep -q 'worker.*Up' && DOCKER_WORKER="YES" || fail "WORKER_NOT_UP"
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    env_snapshot="$(
      cd "$BACKEND_DIR" &&
      docker compose exec -T worker python - <<'PY'
import os
keys = [
    "TESTNET_EXCHANGE_BASE_URL",
    "TESTNET_EXCHANGE_API_KEY",
    "TESTNET_EXCHANGE_API_SECRET",
    "TESTNET_EXCHANGE_KEY_ID",
    "TESTNET_EXECUTOR_MODE",
    "TESTNET_EXECUTOR_REAL_ENABLE",
]
for key in keys:
    value = os.getenv(key)
    if value is None:
        state = "MISSING"
    elif value == "":
        state = "EMPTY"
    else:
        state = "PRESENT"
    print(f"{key}={state}")
if str(os.getenv("TESTNET_EXECUTOR_MODE") or "").strip().lower() == "real":
    print("TESTNET_EXECUTOR_MODE_EFFECTIVE=REAL")
else:
    print("TESTNET_EXECUTOR_MODE_EFFECTIVE=OTHER")
if str(os.getenv("TESTNET_EXECUTOR_REAL_ENABLE") or "").strip() == "1":
    print("TESTNET_EXECUTOR_REAL_ENABLE_EFFECTIVE=ONE")
else:
    print("TESTNET_EXECUTOR_REAL_ENABLE_EFFECTIVE=OTHER")
PY
    )" || fail "WORKER_ENV_CHECK_FAILED"
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    echo "$env_snapshot" | grep -q '^TESTNET_EXCHANGE_BASE_URL=PRESENT$' \
      && TESTNET_EXCHANGE_BASE_URL_PRESENT="YES" || fail "TESTNET_EXCHANGE_BASE_URL_MISSING"
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$env_snapshot" | grep -q '^TESTNET_EXCHANGE_API_KEY=PRESENT$' \
        && TESTNET_EXCHANGE_API_KEY_PRESENT="YES" || fail "TESTNET_EXCHANGE_API_KEY_MISSING"
    fi
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$env_snapshot" | grep -q '^TESTNET_EXCHANGE_API_SECRET=PRESENT$' \
        && TESTNET_EXCHANGE_API_SECRET_PRESENT="YES" || fail "TESTNET_EXCHANGE_API_SECRET_MISSING"
    fi
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$env_snapshot" | grep -q '^TESTNET_EXCHANGE_KEY_ID=PRESENT$' \
        && TESTNET_EXCHANGE_KEY_ID_PRESENT="YES" || fail "TESTNET_EXCHANGE_KEY_ID_MISSING"
    fi
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$env_snapshot" | grep -q '^TESTNET_EXECUTOR_MODE_EFFECTIVE=REAL$' \
        && TESTNET_EXECUTOR_MODE_REAL="YES" || fail "TESTNET_EXECUTOR_MODE_NOT_REAL"
    fi
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$env_snapshot" | grep -q '^TESTNET_EXECUTOR_REAL_ENABLE_EFFECTIVE=ONE$' \
        && TESTNET_EXECUTOR_REAL_ENABLE_ONE="YES" || fail "TESTNET_EXECUTOR_REAL_ENABLE_NOT_ONE"
    fi
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    if curl_health_with_retry; then
      HEALTH_RESULT="PASS"
    else
      fail "BACKEND_HEALTH_UNREACHABLE"
    fi
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    ops_state_json="$(curl_json_with_retry "/ops/state")" || fail "OPS_STATE_UNREACHABLE"
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$ops_state_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(0 if isinstance(data,dict) and "kill_switch" in data and "worker_heartbeat" in data else 1)' \
        && OPS_STATE_RESULT="PASS" || fail "OPS_STATE_INVALID"
    fi
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$ops_state_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(0 if data.get("kill_switch",{}).get("enabled") is False else 1)' \
        && KILL_SWITCH_RESULT="PASS" || fail "KILL_SWITCH_NOT_FALSE"
    fi
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    ops_worker_json="$(curl_json_with_retry "/ops/worker")" || fail "OPS_WORKER_UNREACHABLE"
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$ops_worker_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(0 if isinstance(data,dict) and "telegram_enabled" in data and "last_heartbeat_at" in data else 1)' \
        && OPS_WORKER_RESULT="PASS" || fail "OPS_WORKER_INVALID"
    fi
    if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
      echo "$ops_worker_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(0 if data.get("telegram_enabled") is True else 1)' \
        && TELEGRAM_ENABLED_RESULT="PASS" || fail "TELEGRAM_ENABLED_FALSE"
    fi
  fi

  if [[ "$PASS_OR_FAIL" == "PASS" ]]; then
    echo "$ops_state_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); heartbeat=data.get("worker_heartbeat"); sys.exit(0 if isinstance(heartbeat,dict) and bool(heartbeat.get("last_heartbeat_at")) and bool(heartbeat.get("last_seen_at")) else 1)' \
      && WORKER_HEARTBEAT_RESULT="PASS" || fail "WORKER_HEARTBEAT_NOT_PRESENT"
  fi
fi

echo "[Local Testnet Runtime Check Result]"
echo "canonical env:"
echo "- TESTNET_EXCHANGE_BASE_URL_PRESENT: $TESTNET_EXCHANGE_BASE_URL_PRESENT"
echo "- TESTNET_EXCHANGE_API_KEY_PRESENT: $TESTNET_EXCHANGE_API_KEY_PRESENT"
echo "- TESTNET_EXCHANGE_API_SECRET_PRESENT: $TESTNET_EXCHANGE_API_SECRET_PRESENT"
echo "- TESTNET_EXCHANGE_KEY_ID_PRESENT: $TESTNET_EXCHANGE_KEY_ID_PRESENT"
echo "- TESTNET_EXECUTOR_MODE=real: $TESTNET_EXECUTOR_MODE_REAL"
echo "- TESTNET_EXECUTOR_REAL_ENABLE=1: $TESTNET_EXECUTOR_REAL_ENABLE_ONE"
echo "docker:"
echo "- backend: $DOCKER_BACKEND"
echo "- worker: $DOCKER_WORKER"
echo "endpoints:"
echo "- /health: $HEALTH_RESULT"
echo "- /ops/state: $OPS_STATE_RESULT"
echo "- /ops/worker: $OPS_WORKER_RESULT"
echo "- kill_switch_enabled=false: $KILL_SWITCH_RESULT"
echo "- worker_heartbeat_alive: $WORKER_HEARTBEAT_RESULT"
echo "- telegram_enabled=true: $TELEGRAM_ENABLED_RESULT"
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

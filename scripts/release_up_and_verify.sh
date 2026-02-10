#!/usr/bin/env bash
# One-shot: bring up backend + single Next on 3000, run verify_all_e2e, print delivery template.
# Wrapper only; does not modify verify_all_e2e.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONSOLE_DIR="${CONSOLE_DIR:-$ROOT/anchor-console}"
BACKEND_DIR="${BACKEND_DIR:-$ROOT/anchor-backend}"
NEXT_LOG_FILE="${NEXT_LOG_FILE:-/tmp/next-dev.log}"
VERIFY_OUT="${VERIFY_OUT:-/tmp/verify_all_e2e_release.out}"

# Hard timeout for curl readiness (seconds)
NEXT_READY_TIMEOUT="${NEXT_READY_TIMEOUT:-60}"

# Docker retry on transient pull/auth/network
DOCKER_UP_LOG="${DOCKER_UP_LOG:-/tmp/release_docker_up.log}"
MAX_RETRIES="${RELEASE_DOCKER_MAX_RETRIES:-3}"
# Backoff seconds before retry 1, 2, 3
BACKOFF_1=2
BACKOFF_2=5
BACKOFF_3=10

# Single regex to detect transient docker pull/auth/network errors
TRANSIENT_PATTERN="failed to solve|pull access denied|unauthorized|TLS handshake timeout|i/o timeout|connection reset by peer|net/http: TLS handshake timeout|dial tcp|temporary failure in name resolution|context deadline exceeded|unexpected EOF"

echo "=============================="
echo "release_up_and_verify: Step A — Backend up"
echo "=============================="
cd "$BACKEND_DIR"

if [ "${RELEASE_SIMULATE_DOCKER_PULL_FAIL:-0}" = "1" ]; then
  echo "Simulating transient docker pull failure (RELEASE_SIMULATE_DOCKER_PULL_FAIL=1)..."
  : > "$DOCKER_UP_LOG"
  attempt=1
  while [ "$attempt" -le "$MAX_RETRIES" ]; do
    echo "Attempt $attempt/$MAX_RETRIES (simulated transient failure)"
    echo "failed to solve: failed to fetch oauth token: read tcp: connection reset by peer" >> "$DOCKER_UP_LOG"
    if [ "$attempt" -lt "$MAX_RETRIES" ]; then
      backoff_sec=$BACKOFF_1
      [ "$attempt" -eq 2 ] && backoff_sec=$BACKOFF_2
      echo "Sleeping ${backoff_sec}s before retry..."
      sleep "$backoff_sec"
    fi
    attempt=$((attempt + 1))
  done
  echo "=============================="
  echo "MODULE=release_up_and_verify"
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=DOCKER_PULL_TRANSIENT"
  echo "DOCKER_UP_LOG=$DOCKER_UP_LOG"
  echo "=============================="
  echo "Last ~80 lines of docker log:"
  tail -n 80 "$DOCKER_UP_LOG" 2>/dev/null || true
  exit 1
fi

PS_OUT="$(docker compose ps 2>/dev/null | grep -E 'backend|worker' || true)"
echo "$PS_OUT" | grep -q 'backend.*Up' && BACKEND_UP=1 || BACKEND_UP=0
echo "$PS_OUT" | grep -q 'worker.*Up' && WORKER_UP=1 || WORKER_UP=0

if [ "$BACKEND_UP" -eq 0 ] || [ "$WORKER_UP" -eq 0 ]; then
  attempt=1
  DOCKER_OK=0
  while [ "$attempt" -le "$MAX_RETRIES" ]; do
    echo "Starting backend + worker (docker compose up -d --build) attempt $attempt/$MAX_RETRIES..."
    docker_exit=0
    (docker compose up -d --build > "$DOCKER_UP_LOG" 2>&1) || docker_exit=$?
    if [ "$docker_exit" -eq 0 ]; then
      DOCKER_OK=1
      echo "OK: backend + worker started"
      break
    fi
    if grep -qEi "$TRANSIENT_PATTERN" "$DOCKER_UP_LOG" 2>/dev/null; then
      if [ "$attempt" -lt "$MAX_RETRIES" ]; then
        backoff_sec=$BACKOFF_1
        [ "$attempt" -eq 2 ] && backoff_sec=$BACKOFF_2
        echo "Transient pull/auth/network error detected. Sleeping ${backoff_sec}s before retry..."
        sleep "$backoff_sec"
      else
        echo "=============================="
        echo "MODULE=release_up_and_verify"
        echo "PASS_OR_FAIL=FAIL"
        echo "FAIL_REASON=DOCKER_PULL_TRANSIENT"
        echo "DOCKER_UP_LOG=$DOCKER_UP_LOG"
        echo "=============================="
        echo "Last ~80 lines of docker log:"
        tail -n 80 "$DOCKER_UP_LOG" 2>/dev/null || true
        exit 1
      fi
    else
      echo "=============================="
      echo "MODULE=release_up_and_verify"
      echo "PASS_OR_FAIL=FAIL"
      echo "FAIL_REASON=DOCKER_COMPOSE_UP_FAILED"
      echo "DOCKER_UP_LOG=$DOCKER_UP_LOG"
      echo "=============================="
      echo "Last ~80 lines of docker log:"
      tail -n 80 "$DOCKER_UP_LOG" 2>/dev/null || true
      exit 1
    fi
    attempt=$((attempt + 1))
  done
  [ "$DOCKER_OK" -eq 0 ] && exit 1
else
  echo "OK: backend + worker already Up"
fi
echo

echo "=============================="
echo "release_up_and_verify: Step B — Next single instance on 3000"
echo "=============================="
pids="$(lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $2}' | sort -u || true)"
if [ -n "$pids" ]; then
  echo "Killing existing listener(s) on 3000: $pids"
  echo "$pids" | xargs kill 2>/dev/null || true
  sleep 2
  # Force kill if still present
  pids="$(lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $2}' | sort -u || true)"
  [ -n "$pids" ] && echo "$pids" | xargs kill -9 2>/dev/null || true
  sleep 1
fi

rm -f "$CONSOLE_DIR/.next/dev/lock" 2>/dev/null || true

echo "Starting Next dev (log: $NEXT_LOG_FILE)..."
(cd "$CONSOLE_DIR" && nohup npm run dev >"$NEXT_LOG_FILE" 2>&1 &)
echo

echo "Waiting for http://127.0.0.1:3000/ to return 200 (timeout ${NEXT_READY_TIMEOUT}s)..."
waited=0
while [ "$waited" -lt "$NEXT_READY_TIMEOUT" ]; do
  if curl -sS -o /dev/null -w '%{http_code}' -I --connect-timeout 2 --max-time 5 "http://127.0.0.1:3000/" 2>/dev/null | grep -q '^200$'; then
    echo "OK: Next ready (200) after ${waited}s"
    break
  fi
  sleep 2
  waited=$((waited + 2))
done

if [ "$waited" -ge "$NEXT_READY_TIMEOUT" ]; then
  echo "FAIL: Next did not return 200 within ${NEXT_READY_TIMEOUT}s. Check $NEXT_LOG_FILE"
  exit 1
fi
echo

echo "=============================="
echo "release_up_and_verify: Step C — verify_all_e2e"
echo "=============================="
cd "$ROOT"
VERIFY_EXIT=0
NEXT_LOG_FILE="$NEXT_LOG_FILE" ./scripts/verify_all_e2e.sh 2>&1 | tee "$VERIFY_OUT" || VERIFY_EXIT=$?

if [ "$VERIFY_EXIT" -ne 0 ]; then
  echo "=============================="
  echo "release_up_and_verify: verify_all failed (exit $VERIFY_EXIT)"
  echo "=============================="
  echo "NEXT_LOG_FILE=$NEXT_LOG_FILE"
  echo "VERIFY_ALL_OUT=$VERIFY_OUT"
  echo "Check checklist outputs under /tmp/checklist_*_last.out"
  exit 1
fi
echo

echo "=============================="
echo "release_up_and_verify: Step D — Delivery template"
echo "=============================="
CHECKLIST_DETAIL_EXPLAINER_OUT="/tmp/checklist_detail_explainer_e2e_last.out"
CHECKLIST_CREATE_NAV_EVENTS_OUT="/tmp/checklist_create_navigate_events_e2e_last.out"
CHECKLIST_CREATE_FORM_UI_OUT="/tmp/checklist_create_form_ui_e2e_last.out"
CHECKLIST_LIST_RETRY_UI_OUT="/tmp/checklist_list_retry_ui_e2e_last.out"
CHECKLIST_EVENTS_OUT="/tmp/checklist_events_e2e_last.out"
CHECKLIST_RETRY_OUT="/tmp/checklist_retry_e2e_last.out"

echo "MODULE=release_up_and_verify"
echo "NEXT_LOG_FILE=$NEXT_LOG_FILE"
echo "VERIFY_ALL_OUT=$VERIFY_OUT"
echo "CHECKLIST_DETAIL_EXPLAINER_OUT=$CHECKLIST_DETAIL_EXPLAINER_OUT"
echo "CHECKLIST_CREATE_NAV_EVENTS_OUT=$CHECKLIST_CREATE_NAV_EVENTS_OUT"
echo "CHECKLIST_CREATE_FORM_UI_OUT=$CHECKLIST_CREATE_FORM_UI_OUT"
echo "CHECKLIST_LIST_RETRY_UI_OUT=$CHECKLIST_LIST_RETRY_UI_OUT"
echo "CHECKLIST_EVENTS_OUT=$CHECKLIST_EVENTS_OUT"
echo "CHECKLIST_RETRY_OUT=$CHECKLIST_RETRY_OUT"
echo "PASS_OR_FAIL=PASS"
echo "FAIL_REASON="

#!/usr/bin/env bash
# Worker Panic Guard E2E: inject exceptions -> threshold -> WORKER_PANIC event + Redis kill switch ON.
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_worker_panic_guard_e2e_last.out}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"
ANCHOR_BACKEND_DIR="${ANCHOR_BACKEND_DIR:-$(cd "$(dirname "$0")/.." && pwd)/anchor-backend}"
BACKEND_DIR="${BACKEND_DIR:-$ANCHOR_BACKEND_DIR}"

PASS_OR_FAIL=FAIL
FAIL_REASON=""
PANIC_TRIGGERED=NO
KILL_SWITCH_REDIS_ON=NO
EVENTS_HAS_WORKER_PANIC=NO

echo "=============================="
echo "MODULE=worker_panic_guard_e2e"
echo "Step0: Precheck backend"
echo "=============================="
if ! curl -sS --noproxy '*' -o /dev/null -w "%{http_code}" "$BACKEND_PRECHECK/health" | grep -q 200; then
  echo "PANIC_TRIGGERED=$PANIC_TRIGGERED" > "$OUT"
  echo "KILL_SWITCH_REDIS_ON=$KILL_SWITCH_REDIS_ON" >> "$OUT"
  echo "EVENTS_HAS_WORKER_PANIC=$EVENTS_HAS_WORKER_PANIC" >> "$OUT"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL" >> "$OUT"
  echo "FAIL_REASON=backend_not_reachable" >> "$OUT"
  cat "$OUT"
  exit 1
fi
echo "OK: backend reachable"

echo "=============================="
echo "Step1: Ensure kill switch Redis OFF"
echo "=============================="
curl_opts=( -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":false}' )
[ -n "${OPS_TOKEN:-}" ] && curl_opts+=( -H "x-ops-token: $OPS_TOKEN" )
curl "${curl_opts[@]}" "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
sleep 2
echo "OK: kill switch OFF"

echo "=============================="
echo "Step2: Restart worker with panic threshold + inject"
echo "=============================="
cd "$ANCHOR_BACKEND_DIR"
docker compose -f "$BACKEND_DIR/docker-compose.yml" stop worker 2>/dev/null || true
WORKER_PANIC_THRESHOLD=3 WORKER_PANIC_WINDOW_SECONDS=10 WORKER_PANIC_COOLDOWN_SECONDS=3 WORKER_INJECT_PANIC=1 \
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker
sleep 8
echo "OK: worker restarted with inject"

echo "=============================="
echo "Step3: Check Redis kill switch ON"
echo "=============================="
kill_switch_json="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/ops/kill-switch")"
enabled="$(echo "$kill_switch_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('enabled', False))" 2>/dev/null || echo "false")"
source_val="$(echo "$kill_switch_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('source',''))" 2>/dev/null || echo "")"
if [ "$enabled" = "True" ] && [ "$source_val" = "redis" ]; then
  KILL_SWITCH_REDIS_ON=YES
  PANIC_TRIGGERED=YES
fi
if [ "$KILL_SWITCH_REDIS_ON" != "YES" ]; then
  echo "PANIC_TRIGGERED=$PANIC_TRIGGERED" > "$OUT"
  echo "KILL_SWITCH_REDIS_ON=$KILL_SWITCH_REDIS_ON" >> "$OUT"
  echo "EVENTS_HAS_WORKER_PANIC=$EVENTS_HAS_WORKER_PANIC" >> "$OUT"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL" >> "$OUT"
  echo "FAIL_REASON=kill_switch_redis_not_on" >> "$OUT"
  # Cleanup
  docker compose -f "$BACKEND_DIR/docker-compose.yml" stop worker 2>/dev/null || true
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  sleep 2
  curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":false}' "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "OK: kill switch Redis ON"

echo "=============================="
echo "Step4: Check events for WORKER_PANIC"
echo "=============================="
events="$(curl -sS --noproxy '*' "$BACKEND_PRECHECK/domain-commands/ops-worker/events?limit=200")"
has_panic="$(echo "$events" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for e in data:
    if e.get('event_type') == 'WORKER_PANIC':
        print('yes')
        sys.exit(0)
print('no')
" 2>/dev/null || echo "no")"
if [ "$has_panic" = "yes" ]; then
  EVENTS_HAS_WORKER_PANIC=YES
fi
if [ "$EVENTS_HAS_WORKER_PANIC" != "YES" ]; then
  echo "PANIC_TRIGGERED=$PANIC_TRIGGERED" > "$OUT"
  echo "KILL_SWITCH_REDIS_ON=$KILL_SWITCH_REDIS_ON" >> "$OUT"
  echo "EVENTS_HAS_WORKER_PANIC=$EVENTS_HAS_WORKER_PANIC" >> "$OUT"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL" >> "$OUT"
  echo "FAIL_REASON=events_missing_worker_panic" >> "$OUT"
  # Cleanup
  docker compose -f "$BACKEND_DIR/docker-compose.yml" stop worker 2>/dev/null || true
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
  sleep 2
  curl -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":false}' "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
  cat "$OUT"
  exit 1
fi
echo "OK: WORKER_PANIC in events"

echo "=============================="
echo "Cleanup: Restore worker + kill switch OFF"
echo "=============================="
docker compose -f "$BACKEND_DIR/docker-compose.yml" stop worker 2>/dev/null || true
docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d worker 2>/dev/null || true
sleep 2
curl_opts=( -sS --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"enabled":false}' )
[ -n "${OPS_TOKEN:-}" ] && curl_opts+=( -H "x-ops-token: $OPS_TOKEN" )
curl "${curl_opts[@]}" "$BACKEND_PRECHECK/ops/kill-switch" >/dev/null || true
sleep 2
echo "OK: cleanup done"

PASS_OR_FAIL=PASS
FAIL_REASON=""
{
  echo "MODULE=worker_panic_guard_e2e"
  echo "PANIC_TRIGGERED=$PANIC_TRIGGERED"
  echo "KILL_SWITCH_REDIS_ON=$KILL_SWITCH_REDIS_ON"
  echo "EVENTS_HAS_WORKER_PANIC=$EVENTS_HAS_WORKER_PANIC"
  echo "PASS_OR_FAIL=$PASS_OR_FAIL"
  echo "FAIL_REASON=$FAIL_REASON"
} > "$OUT"
cat "$OUT"
exit 0

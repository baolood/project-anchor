#!/usr/bin/env bash
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_ops_console_e2e_last.out}"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"

PASS_OR_FAIL=PASS
FAIL_REASON=""

echo "MODULE=ops_console_e2e" > "$OUT"

HTTP=$(curl -s -o /tmp/ops_worker.json -w "%{http_code}" "$CONSOLE_URL/api/ops/worker")
echo "WORKER_HTTP_STATUS=$HTTP" >> "$OUT"

if [ "$HTTP" != "200" ]; then
  PASS_OR_FAIL=FAIL
  FAIL_REASON="worker_endpoint_not_200"
fi

HTTP_ON=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "content-type: application/json" \
  -d '{"enabled":true}' \
  "$CONSOLE_URL/api/ops/kill-switch")

echo "SET_ON_HTTP_STATUS=$HTTP_ON" >> "$OUT"

sleep 2

OBS_ON=$(curl -s "$CONSOLE_URL/api/ops/worker" | grep -c '"kill_switch_enabled":true' || true)
echo "OBSERVED_ON=$([ "$OBS_ON" -gt 0 ] && echo YES || echo NO)" >> "$OUT"

HTTP_OFF=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "content-type: application/json" \
  -d '{"enabled":false}' \
  "$CONSOLE_URL/api/ops/kill-switch")

echo "SET_OFF_HTTP_STATUS=$HTTP_OFF" >> "$OUT"

sleep 2

OBS_OFF=$(curl -s "$CONSOLE_URL/api/ops/worker" | grep -c '"kill_switch_enabled":false' || true)
echo "OBSERVED_OFF=$([ "$OBS_OFF" -gt 0 ] && echo YES || echo NO)" >> "$OUT"

if [ "$HTTP_ON" != "200" ] || [ "$HTTP_OFF" != "200" ] || [ "$OBS_ON" -eq 0 ] || [ "$OBS_OFF" -eq 0 ]; then
  PASS_OR_FAIL=FAIL
  FAIL_REASON="kill_switch_toggle_failed"
fi

echo "PASS_OR_FAIL=$PASS_OR_FAIL" >> "$OUT"
echo "FAIL_REASON=$FAIL_REASON" >> "$OUT"

cat "$OUT"
[ "$PASS_OR_FAIL" = "PASS" ] || exit 1
exit 0

#!/usr/bin/env bash
set -e

CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"

echo "Checking /ops page..."

# Client-rendered page: initial HTML may not contain "OPS DASHBOARD"/"Status"/"Heartbeat".
# Use HTTP status + API check instead.
code=$(curl -sS -o /dev/null -w "%{http_code}" --noproxy '*' "$CONSOLE_URL/ops")
[ "$code" = "200" ] || { echo "FAIL: /ops returned $code"; exit 1; }

state=$(curl -sS --noproxy '*' "$CONSOLE_URL/api/proxy/ops/state")
echo "$state" | grep -q '"kill_switch"' || { echo "FAIL: /api/proxy/ops/state missing kill_switch"; exit 1; }
echo "$state" | grep -q '"worker_heartbeat"' || { echo "FAIL: /api/proxy/ops/state missing worker_heartbeat"; exit 1; }

echo "ops_dashboard_ui_e2e PASS"

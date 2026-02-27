#!/usr/bin/env bash
# Phase 3.6: ops_audit.actor from X-ANCHOR-KEY (key:<sha256[:8]>) or anon
set -euo pipefail

BASE="${ANCHOR_BACKEND_URL:-http://127.0.0.1:8000}"
TS="$(date +%s)"
KEY="test-key-${TS}"

echo "== 1) health must OK =="
curl -fsS "$BASE/health" >/dev/null
echo "health=OK"

echo "== 2) toggle twice with X-ANCHOR-KEY =="
curl -fsS -X POST "$BASE/ops/kill-switch" \
  -H 'content-type: application/json' \
  -H "X-ANCHOR-KEY: $KEY" \
  -d '{"enabled": true}' >/dev/null
curl -fsS -X POST "$BASE/ops/kill-switch" \
  -H 'content-type: application/json' \
  -H "X-ANCHOR-KEY: $KEY" \
  -d '{"enabled": false}' >/dev/null
echo "toggle=OK"

echo "== 3) fetch /ops/audit =="
BODY="$(curl -fsS "$BASE/ops/audit?limit=50")"
echo "$BODY" | head -c 1500
echo

echo "== 4) assert KILL_SWITCH_SET and actor key: =="
echo "$BODY" | grep -q 'KILL_SWITCH_SET' || { echo "FAIL: no KILL_SWITCH_SET"; exit 2; }
echo "$BODY" | grep -qE '"actor"[[:space:]]*:[[:space:]]*"key:' || { echo "FAIL: no actor key: (actor from X-ANCHOR-KEY)"; exit 2; }

echo "PASS: Phase 3.6 audit actor"

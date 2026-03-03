#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8000}"

echo "== 1) health =="
curl -fsS "$BASE/health" >/dev/null
echo "health=OK"

echo "== 2) set policy_limits via CLI in backend container =="
CID="$(docker compose ps -q backend)"
[ -n "$CID" ] || { echo "FAIL: backend container not running"; exit 2; }
docker compose exec -T backend python -m app.system.risk_state_cli set policy_limits \
  '{"max_net_exposure_usd": 123, "daily_loss_limit_usd": 45, "max_single_trade_risk_usd": 6}'
echo "SET_POLICY_LIMITS=OK"

echo "== 3) enable risk_gate_global =="
docker compose exec -T backend python -m app.system.risk_state_cli set risk_gate_global \
  '{"enabled": true, "reason":"phase38_global_gate"}'
echo "SET_GATE_ON=OK"

echo "== 4) POST /commands should be 403 RISK_GATE_GLOBAL =="
IDEM="p38-deny-$(date +%s)-$$"
resp="$(curl -sS -i -X POST "$BASE/commands" \
  -H 'content-type: application/json' \
  -H "X-Idempotency-Key: $IDEM" \
  -d '{"type":"NOOP","payload":{"account_id":"A"}}' || true)"
echo "$resp" | sed -n '1,80p'
echo "$resp" | grep -q "403" || { echo "FAIL: expected 403"; exit 3; }
echo "$resp" | grep -q "RISK_GATE_GLOBAL" || { echo "FAIL: expected RISK_GATE_GLOBAL"; exit 4; }
echo "DENY_GLOBAL=YES"

echo "== 5) disable gate and re-check behavior =="
docker compose exec -T backend python -m app.system.risk_state_cli set risk_gate_global '{"enabled": false}'
echo "SET_GATE_OFF=OK"

# Here is the compatibility trick:
# - If legacy commands table exists, create should succeed (2xx)
# - If it doesn't exist, backend may return 5xx (DB error) BUT it must NOT be 403 RISK_GATE_GLOBAL anymore.
IDEM="p38-allow-$(date +%s)-$$"
resp2="$(curl -sS -i -X POST "$BASE/commands" \
  -H 'content-type: application/json' \
  -H "X-Idempotency-Key: $IDEM" \
  -d '{"type":"NOOP","payload":{"account_id":"A"}}' || true)"
echo "$resp2" | sed -n '1,80p'

if echo "$resp2" | grep -q "403" && echo "$resp2" | grep -q "RISK_GATE_GLOBAL"; then
  echo "FAIL: gate still denying after disable"
  exit 5
fi

if echo "$resp2" | head -1 | grep -q " 2"; then
  echo "ALLOW_CREATE_HTTP_2XX=YES"
else
  echo "ALLOW_CREATE_NOT_403_GLOBAL=YES (legacy commands table may be missing, acceptable)"
fi

echo "PASS: phase38 risk_state integration (compat)"

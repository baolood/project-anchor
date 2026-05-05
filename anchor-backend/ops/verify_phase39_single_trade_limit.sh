#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8000}"

echo "== 1) set limit =="
docker compose exec -T backend python -m app.system.risk_state_cli set policy_limits \
  '{"max_single_trade_risk_usd":5}'

echo "== 2) trade within limit (should pass) =="
resp=$(curl -sS -X POST "$BASE/commands" \
  -H "content-type: application/json" \
  -H "X-Idempotency-Key: p39-allow-$(date +%s)-$$" \
  -d '{"type":"NOOP","payload":{"account_id":"A","risk_usd":3}}')
echo "$resp"
echo "$resp" | grep -q '"id"\|"status"' && echo "ALLOW_OK" || { echo "FAIL: expected 2xx with id"; exit 2; }

echo "== 3) trade exceeding limit (should deny) =="
resp2=$(curl -sS -i -X POST "$BASE/commands" \
  -H "content-type: application/json" \
  -H "X-Idempotency-Key: p39-deny-$(date +%s)-$$" \
  -d '{"type":"NOOP","payload":{"account_id":"A","risk_usd":8}}')
echo "$resp2" | head -20
echo "$resp2" | grep -q "403" || { echo "FAIL: expected 403"; exit 3; }
echo "$resp2" | grep -q "MAX_SINGLE_TRADE_RISK" || { echo "FAIL: expected MAX_SINGLE_TRADE_RISK"; exit 4; }
echo "DENY_LIMIT=YES"

echo "PASS: phase39 single trade limit"

#!/usr/bin/env bash
# Verify observability loop: risk_gate / policy_engine / idempotency → ops_audit
# - COMMAND_CREATE_DENIED (risk_gate_global, MAX_SINGLE_TRADE_RISK)
# - IDEMPOTENCY_CONFLICT (same key different body)
# - COMMAND_CREATE_ACCEPTED (success)
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT/anchor-backend"
BASE="${BASE:-http://127.0.0.1:8000}"
JSON_CT='content-type: application/json'

echo "== 1) health =="
curl -fsS "$BASE/health" >/dev/null
echo "health=OK"

echo "== 2) ensure ops_audit + idempotency_keys =="
PG="$(docker compose ps -q postgres)"
[ -n "$PG" ] || { echo "FAIL: postgres not running"; exit 2; }
for f in ops/sql/phase34_ops_audit.sql ops/sql/phase310_idempotency_keys.sql; do
  [ -f "$f" ] && docker exec -i "$PG" psql -U anchor -d anchor < "$f" || true
done
echo "SQL_OK"

echo "== 3) risk_gate_global → COMMAND_CREATE_DENIED =="
docker compose exec -T backend python -m app.system.risk_state_cli set risk_gate_global '{"enabled": true, "reason":"verify_obs_global"}'
KEY_DENY="obs-deny-$(date +%s)"
r="$(curl -sS -i -X POST "$BASE/commands" -H "$JSON_CT" -H "X-Idempotency-Key: $KEY_DENY" -H "X-ANCHOR-KEY: obs-key" -d '{"type":"NOOP","payload":{"risk_usd":1}}')"
echo "$r" | head -12
echo "$r" | grep -qE '^HTTP/.* 403' || { echo "FAIL: expected 403 for risk_gate_global"; exit 3; }
aud="$(curl -fsS "$BASE/ops/audit?limit=20")"
echo "$aud" | grep -q "COMMAND_CREATE_DENIED" || { echo "FAIL: audit missing COMMAND_CREATE_DENIED"; exit 3; }
echo "$aud" | grep -q "RISK_GATE_GLOBAL" || { echo "FAIL: audit missing RISK_GATE_GLOBAL"; exit 3; }
echo "DENIED_GLOBAL=YES"

docker compose exec -T backend python -m app.system.risk_state_cli set risk_gate_global '{"enabled": false}'

echo "== 4) MAX_SINGLE_TRADE_RISK → COMMAND_CREATE_DENIED =="
docker compose exec -T backend python -m app.system.risk_state_cli set policy_limits '{"max_single_trade_risk_usd":5}'
KEY_POLICY="obs-policy-$(date +%s)"
r2="$(curl -sS -i -X POST "$BASE/commands" -H "$JSON_CT" -H "X-Idempotency-Key: $KEY_POLICY" -H "X-ANCHOR-KEY: obs-key" -d '{"type":"NOOP","payload":{"risk_usd":8}}')"
echo "$r2" | head -12
echo "$r2" | grep -qE '^HTTP/.* 403' || { echo "FAIL: expected 403 for MAX_SINGLE_TRADE_RISK"; exit 4; }
echo "$r2" | grep -q "MAX_SINGLE_TRADE_RISK" || { echo "FAIL: response missing MAX_SINGLE_TRADE_RISK"; exit 4; }
aud2="$(curl -fsS "$BASE/ops/audit?limit=30")"
echo "$aud2" | grep -q "MAX_SINGLE_TRADE_RISK" || { echo "FAIL: audit missing MAX_SINGLE_TRADE_RISK"; exit 4; }
echo "DENIED_POLICY=YES"

echo "== 5) idempotency conflict → IDEMPOTENCY_CONFLICT =="
# Use risk_usd within limit (5) so only idempotency is checked
KEY_IDEM="obs-idem-$(date +%s)"
curl -fsS -X POST "$BASE/commands" -H "$JSON_CT" -H "X-Idempotency-Key: $KEY_IDEM" -H "X-ANCHOR-KEY: obs-key" -d '{"type":"noop","payload":{"risk_usd":2}}' >/dev/null
r3="$(curl -sS -i -X POST "$BASE/commands" -H "$JSON_CT" -H "X-Idempotency-Key: $KEY_IDEM" -H "X-ANCHOR-KEY: obs-key" -d '{"type":"noop","payload":{"risk_usd":3}}')"
echo "$r3" | head -12
echo "$r3" | grep -qE '^HTTP/.* 409' || { echo "FAIL: expected 409 for idempotency conflict"; exit 5; }
aud3="$(curl -fsS "$BASE/ops/audit?limit=50")"
echo "$aud3" | grep -q "IDEMPOTENCY_CONFLICT" || { echo "FAIL: audit missing IDEMPOTENCY_CONFLICT"; exit 5; }
echo "IDEM_CONFLICT=YES"

echo "== 6) success → COMMAND_CREATE_ACCEPTED =="
KEY_ACC="obs-acc-$(date +%s)"
r4="$(curl -sS -X POST "$BASE/commands" -H "$JSON_CT" -H "X-Idempotency-Key: $KEY_ACC" -H "X-ANCHOR-KEY: obs-key" -d '{"type":"noop","payload":{"risk_usd":1}}')"
echo "$r4" | grep -q '"id"' || { echo "FAIL: expected 2xx with id"; exit 6; }
aud4="$(curl -fsS "$BASE/ops/audit?limit=50")"
echo "$aud4" | grep -q "COMMAND_CREATE_ACCEPTED" || { echo "FAIL: audit missing COMMAND_CREATE_ACCEPTED"; exit 6; }
echo "$aud4" | grep -q "$KEY_ACC" || { echo "FAIL: audit missing idempotency_key"; exit 6; }
echo "ACCEPTED=YES"

echo "PASS: observability loop (risk_gate / policy / idempotency → ops_audit)"

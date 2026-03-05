#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT/anchor-backend"

BASE="${BASE:-http://127.0.0.1:8000}"
KEY="phase311-$(date +%s)"
ANCHOR_KEY="test-key-phase311-$(date +%s)"
JSON_CT='content-type: application/json'

echo "== 1) health =="
curl -fsS "$BASE/health" >/dev/null
echo "health=OK"

echo "== 2) apply sql (ops_audit + idempotency_keys) =="
PG="$(docker compose ps -q postgres)"
[ -n "$PG" ] || { echo "FAIL: postgres container not running"; exit 2; }

# ops_audit (Phase 3.4)
if [ -f "ops/sql/phase34_ops_audit.sql" ]; then
  docker exec -i "$PG" psql -U anchor -d anchor < ops/sql/phase34_ops_audit.sql
else
  echo "WARN: ops/sql/phase34_ops_audit.sql missing; assuming ops_audit exists"
fi

# idempotency_keys (Phase 3.10)
if [ -f "ops/sql/phase310_idempotency_keys.sql" ]; then
  docker exec -i "$PG" psql -U anchor -d anchor < ops/sql/phase310_idempotency_keys.sql
else
  echo "FAIL: ops/sql/phase310_idempotency_keys.sql missing"
  exit 2
fi
echo "SQL_OK"

echo "== 3) restart backend =="
docker compose up -d --build backend >/dev/null
sleep 2
curl -fsS "$BASE/health" >/dev/null
echo "backend=OK"

echo "== 4) same key + same body (expect 2xx twice; second should be cached hit) =="
BODY_OK='{"type":"noop","payload":{"risk_usd":3}}'

r1="$(curl -sS -i -X POST "$BASE/commands" \
  -H "$JSON_CT" -H "X-Idempotency-Key: $KEY" -H "X-ANCHOR-KEY: $ANCHOR_KEY" \
  -d "$BODY_OK")"
echo "$r1" | head -15

r2="$(curl -sS -i -X POST "$BASE/commands" \
  -H "$JSON_CT" -H "X-Idempotency-Key: $KEY" -H "X-ANCHOR-KEY: $ANCHOR_KEY" \
  -d "$BODY_OK")"
echo "$r2" | head -15

echo "$r1" | grep -qE '^HTTP/.* 2' || { echo "FAIL: first request not 2xx"; exit 3; }
echo "$r2" | grep -qE '^HTTP/.* 2' || { echo "FAIL: second request not 2xx"; exit 3; }
echo "IDEM_SAME_2XX=YES"

echo "== 5) same key + different body (expect 409 conflict) =="
BODY_BAD='{"type":"noop","payload":{"risk_usd":9}}'
r3="$(curl -sS -i -X POST "$BASE/commands" \
  -H "$JSON_CT" -H "X-Idempotency-Key: $KEY" -H "X-ANCHOR-KEY: $ANCHOR_KEY" \
  -d "$BODY_BAD")"
echo "$r3" | head -20
echo "$r3" | grep -qE '^HTTP/.* 409' || { echo "FAIL: conflict not 409"; exit 4; }
echo "IDEM_CONFLICT_409=YES"

echo "== 6) audit must contain IDEMPOTENCY_* with this key =="
aud="$(curl -fsS "$BASE/ops/audit?limit=200")"
echo "$aud" | head -c 500; echo

echo "$aud" | grep -q "IDEMPOTENCY" || { echo "FAIL: audit has no IDEMPOTENCY"; exit 5; }
echo "$aud" | grep -q "$KEY" || { echo "FAIL: audit missing key=$KEY"; exit 5; }

echo "PASS: phase311 idempotency audit"

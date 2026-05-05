#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8000}"

echo "== 1) health =="
curl -fsS "$BASE/health" >/dev/null
echo "health=OK"

echo "== 2) apply SQL (idempotency_keys) =="
cd "$(git rev-parse --show-toplevel)/anchor-backend"
PG="$(docker compose ps -q postgres)"
[ -n "$PG" ] || { echo "FAIL: postgres not running"; exit 2; }
docker exec -i "$PG" psql -U anchor -d anchor < ops/sql/phase310_idempotency_keys.sql
echo "SQL_OK"

echo "== 3) rebuild backend =="
docker compose up -d --build backend
sleep 2

echo "== 4) set policy_limits small (optional) =="
true

echo "== 5) idem same request twice => second returns same response =="
KEY="idem-$(date +%s)"
PAY='{"type":"NOOP","payload":{"risk_usd":1}}'

r1="$(curl -sS -i -H "content-type: application/json" -H "X-Idempotency-Key: $KEY" -d "$PAY" "$BASE/commands")"
echo "$r1" | head -20
code1="$(echo "$r1" | awk 'NR==1{print $2}')"
[ "$code1" = "200" ] || [ "$code1" = "201" ] || [ "$code1" = "202" ] || { echo "FAIL: first request not 2xx"; exit 3; }

body1="$(echo "$r1" | sed -n '/^\r$/,$p' | tail -n +2)"
r2="$(curl -sS -i -H "content-type: application/json" -H "X-Idempotency-Key: $KEY" -d "$PAY" "$BASE/commands")"
code2="$(echo "$r2" | awk 'NR==1{print $2}')"
[ "$code2" = "200" ] || [ "$code2" = "201" ] || [ "$code2" = "202" ] || { echo "FAIL: second request not 2xx"; exit 4; }
body2="$(echo "$r2" | sed -n '/^\r$/,$p' | tail -n +2)"

if [ "$body1" != "$body2" ]; then
  echo "FAIL: idempotent response mismatch"
  echo "BODY1=$body1"
  echo "BODY2=$body2"
  exit 5
fi
echo "IDEM_SAME_OK=YES"

echo "== 6) same key different request => 409 =="
PAY2='{"type":"NOOP","payload":{"risk_usd":2}}'
r3="$(curl -sS -i -H "content-type: application/json" -H "X-Idempotency-Key: $KEY" -d "$PAY2" "$BASE/commands" || true)"
echo "$r3" | head -20
code3="$(echo "$r3" | awk 'NR==1{print $2}')"
[ "$code3" = "409" ] || { echo "FAIL: expected 409"; exit 6; }
echo "IDEM_CONFLICT_409=YES"

echo "PASS: phase310 idempotency keys"

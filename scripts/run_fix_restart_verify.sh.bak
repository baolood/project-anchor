#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/baolood/Projects/project-anchor}"
BACKEND="${BACKEND:-$ROOT/anchor-backend}"
CONSOLE="${CONSOLE:-$ROOT/anchor-console}"

CONSOLE_PRECHECK="${CONSOLE_PRECHECK:-http://127.0.0.1:3000}"
BACKEND_PRECHECK="${BACKEND_PRECHECK:-http://127.0.0.1:8000}"
ANCHOR_BACKEND_DIR="${ANCHOR_BACKEND_DIR:-$BACKEND}"

PG_USER="${PG_USER:-anchor}"
PG_DB="${PG_DB:-anchor}"

MIGRATION_FILE="${MIGRATION_FILE:-$BACKEND/migrations/0004_domain_events.sql}"

echo "ROOT=$ROOT"
echo "BACKEND=$BACKEND"
echo "CONSOLE=$CONSOLE"
echo "CONSOLE_PRECHECK=$CONSOLE_PRECHECK"
echo "BACKEND_PRECHECK=$BACKEND_PRECHECK"
echo "PG_USER=$PG_USER PG_DB=$PG_DB"
echo "MIGRATION_FILE=$MIGRATION_FILE"
echo

echo "=============================="
echo "STEP 0｜代码快速自检"
echo "=============================="
cd "$BACKEND"

# 仅检查 _domain_mark_failed 内无 type(result)（mark_done 有 result 参数，合法）
if grep -A 35 "async def _domain_mark_failed" app/workers/domain_command_worker.py 2>/dev/null | grep -q "type(result)"; then
  echo "FAIL: _domain_mark_failed 仍存在 type(result) 日志"
  exit 1
fi

# 仅检查 main.py 中 retry 不 bump attempt（worker pick 处应保留 attempt+1）
if grep "attempt = attempt + 1" app/main.py 2>/dev/null; then
  echo "FAIL: retry 仍在 main 中修改 attempt"
  exit 1
fi

echo "OK: code checks pass"
echo

echo "=============================="
echo "STEP 1｜重启 backend + worker（no-cache build）"
echo "=============================="
docker compose down
docker compose build --no-cache backend worker
docker compose up -d

sleep 3
echo "OK: backend/worker up"
echo

echo "=============================="
echo "STEP 2｜应用 migration（domain_events）"
echo "=============================="
if [ ! -f "$MIGRATION_FILE" ]; then
  echo "FAIL: migration file not found: $MIGRATION_FILE"
  exit 1
fi

PG_CID="$(docker compose ps -q postgres || true)"
if [ -z "$PG_CID" ]; then
  echo "FAIL: postgres container not found"
  docker compose ps
  exit 1
fi

docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 < "$MIGRATION_FILE"

# verify exists
docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 -c "\dt domain_events" | sed -n '1,80p'

echo "OK: migration applied (domain_events exists)"
echo

echo "=============================="
echo "STEP 3｜worker 日志必须无 result 未定义"
echo "=============================="
docker compose logs --tail=120 worker | tee /tmp/worker_last.log

if grep -q "name 'result' is not defined" /tmp/worker_last.log; then
  echo "FAIL: worker still shows result undefined"
  exit 1
fi

echo "OK: worker log clean"
echo

echo "=============================="
echo "STEP 4｜确保只有一个 Next 在 3000，启动并落盘日志"
echo "=============================="
pids="$(lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null | awk 'NR>1{print $2}' || true)"
if [ -n "${pids:-}" ]; then
  echo "Killing old Next PIDs: $pids"
  echo "$pids" | xargs kill -9 2>/dev/null || true
fi

rm -f "$CONSOLE/.next/dev/lock" || true

cd "$CONSOLE"
nohup npm run dev > /tmp/next-dev.log 2>&1 &
NEXT_PID="$!"
sleep 5

echo "NEXT_PID=$NEXT_PID"
tail -n 30 /tmp/next-dev.log || true
echo

echo "=============================="
echo "STEP 5｜自检 flaky（backend + console proxy）"
echo "=============================="
curl -sS -i --noproxy '*' -X POST "$BACKEND_PRECHECK/domain-commands/flaky" | sed -n '1,25p'
curl -sS -i --noproxy '*' -X POST "$CONSOLE_PRECHECK/api/proxy/commands/flaky" | sed -n '1,25p'
echo

echo "=============================="
echo "STEP 6｜Retry E2E（PASS 必须）"
echo "=============================="
cp "$ROOT/scripts/checklist_retry_e2e.sh" /tmp/anchor_e2e_checklist_retry_e2e.sh
chmod +x /tmp/anchor_e2e_checklist_retry_e2e.sh

ANCHOR_BACKEND_DIR="$ANCHOR_BACKEND_DIR" \
CONSOLE_PRECHECK="$CONSOLE_PRECHECK" \
BACKEND_PRECHECK="$BACKEND_PRECHECK" \
bash /tmp/anchor_e2e_checklist_retry_e2e.sh | tee /tmp/anchor_e2e_checklist_retry_e2e_last.out

grep -q "PASS_OR_FAIL=PASS" /tmp/anchor_e2e_checklist_retry_e2e_last.out

echo "===== PASTE_1: retry checklist last template ====="
tail -n 80 /tmp/anchor_e2e_checklist_retry_e2e_last.out
echo

echo "=============================="
echo "STEP 7｜Events E2E（PASS 必须）"
echo "=============================="
bash "$ROOT/scripts/checklist_events_e2e.sh" | tee /tmp/anchor_e2e_checklist_events_e2e_last.out
grep -q "PASS_OR_FAIL=PASS" /tmp/anchor_e2e_checklist_events_e2e_last.out

echo "===== PASTE_2: events checklist template ====="
cat /tmp/anchor_e2e_checklist_events_e2e_last.out
echo

echo "=============================="
echo "STEP 8｜Next 日志证据（POST flaky + retry 200）"
echo "=============================="
echo "===== PASTE_3: next dev log grep ====="
grep -E "POST /api/proxy/commands/flaky|POST /api/proxy/commands/.*/retry" /tmp/next-dev.log 2>/dev/null | tail -n 40 || true
echo

echo "=============================="
echo "STEP 9｜worker 日志证据（最新 120 行）"
echo "=============================="
echo "===== PASTE_4: worker logs ====="
cd "$BACKEND"
docker compose logs --tail=120 worker
echo

echo "=============================="
echo "FINAL"
echo "=============================="
echo "PASS_OR_FAIL=PASS"

#!/usr/bin/env bash
set -euo pipefail

echo "=============================="
echo "STEP 0｜路径与环境"
echo "=============================="

ROOT="/Users/baolood/Projects/project-anchor"
BACKEND="$ROOT/anchor-backend"
CONSOLE="$ROOT/anchor-console"

export CONSOLE_PRECHECK="http://127.0.0.1:3000"
export BACKEND_PRECHECK="http://127.0.0.1:8000"
export ANCHOR_BACKEND_DIR="$BACKEND"

echo "ROOT=$ROOT"
echo "BACKEND=$BACKEND"
echo "CONSOLE=$CONSOLE"
echo

echo "=============================="
echo "STEP 1｜代码一致性检查"
echo "=============================="

cd "$BACKEND"

echo "[check] result 未定义 bug 是否已修复（仅检查 _domain_mark_failed 内无 type(result)）"
if grep -A 35 "async def _domain_mark_failed" app/workers/domain_command_worker.py | grep -q "type(result)"; then
  echo "FAIL: _domain_mark_failed 仍引用 result"
  exit 1
else
  echo "OK: result bug 已修复"
fi

echo "[check] retry 是否还在 bump attempt（仅检查 main.py 中 retry 路径）"
if grep "attempt = attempt + 1" app/main.py 2>/dev/null; then
  echo "FAIL: retry 仍在 main 中修改 attempt"
  exit 1
else
  echo "OK: retry attempt 语义正确"
fi

echo

echo "=============================="
echo "STEP 2｜强制重建 backend + worker（no-cache）"
echo "=============================="

docker compose down
docker compose build --no-cache backend worker
docker compose up -d

sleep 3

echo
echo "[check] worker 日志（必须无 result 报错）"
docker compose logs --tail=80 worker

if docker compose logs worker 2>/dev/null | grep -q "name 'result' is not defined"; then
  echo "FAIL: worker 仍在跑旧代码"
  exit 1
fi

echo "OK: worker 正常"
echo

echo "=============================="
echo "STEP 3｜确保只有一个 Next 在 3000"
echo "=============================="

pids=$(lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null | awk 'NR>1{print $2}')
if [ -n "$pids" ]; then
  echo "Killing old next dev: $pids"
  echo "$pids" | xargs kill -9 2>/dev/null || true
fi

rm -f "$CONSOLE/.next/dev/lock" || true

echo "Starting Next dev..."
cd "$CONSOLE"
npm run dev > /tmp/next-dev.log 2>&1 &
NEXT_PID=$!

sleep 5

echo "Next PID=$NEXT_PID"
echo

echo "=============================="
echo "STEP 4｜Retry E2E"
echo "=============================="

cp "$ROOT/scripts/checklist_retry_e2e.sh" /tmp/anchor_e2e_checklist_retry_e2e.sh
chmod +x /tmp/anchor_e2e_checklist_retry_e2e.sh

bash /tmp/anchor_e2e_checklist_retry_e2e.sh | tee /tmp/anchor_e2e_checklist_retry_e2e_last.out

if ! grep -q "PASS_OR_FAIL=PASS" /tmp/anchor_e2e_checklist_retry_e2e_last.out; then
  echo "FAIL: Retry E2E 未通过"
  exit 1
fi

echo
echo "[check] attempt 语义"
grep -E "ATTEMPT_AT_FAIL=|ATTEMPT_AT_DONE=" /tmp/anchor_e2e_checklist_retry_e2e_last.out || true

if grep -q "ATTEMPT_AT_DONE=3" /tmp/anchor_e2e_checklist_retry_e2e_last.out; then
  echo "FAIL: attempt 被多次递增"
  exit 1
fi

echo "OK: Retry E2E 通过"
echo

echo "=============================="
echo "STEP 5｜Events E2E"
echo "=============================="

bash "$ROOT/scripts/checklist_events_e2e.sh" | tee /tmp/anchor_e2e_checklist_events_e2e_last.out

if ! grep -q "PASS_OR_FAIL=PASS" /tmp/anchor_e2e_checklist_events_e2e_last.out; then
  echo "FAIL: Events E2E 未通过"
  exit 1
fi

echo
echo "=============================="
echo "FINAL RESULT"
echo "=============================="
echo "RETRY_E2E=PASS"
echo "EVENTS_E2E=PASS"
echo "PASS_OR_FAIL=PASS"
echo

echo "Artifacts:"
echo "  /tmp/anchor_e2e_checklist_retry_e2e_last.out"
echo "  /tmp/anchor_e2e_checklist_events_e2e_last.out"

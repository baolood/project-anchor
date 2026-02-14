#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 0) 清理旧证据/旧进程（避免 3000/8000 被占用、旧 e2e 输出干扰）
rm -f /tmp/anchor_e2e_* /tmp/anchor_extreme_* 2>/dev/null || true

# 杀掉可能残留的 next/node（可选但建议）
pkill -f "next dev" 2>/dev/null || true
pkill -f "node.*3000" 2>/dev/null || true

# 1) 后端全量重启（含 redis/postgres/worker/backend）
cd "$ROOT/anchor-backend" || exit 1
docker compose down --remove-orphans
docker compose up -d --build
docker compose ps

# 2) 前端依赖与 dev server（单独起一个终端也行；这里用后台方式保证 release 能跑 UI e2e）
cd "$ROOT/anchor-console" || exit 1
npm ci
# 确保 3000 起得来
PORT=3000 nohup npm run dev > /tmp/anchor_console_dev_3000.out 2>&1 &
sleep 5

# 3) 冒烟检查：8000/3000 必须 200
curl -s -o /dev/null -w "BACKEND_HTTP=%{http_code}\n" http://127.0.0.1:8000/health || true
curl -s -o /dev/null -w "CONSOLE_HTTP=%{http_code}\n" http://127.0.0.1:3000/commands || true

# 4) 跑 release（默认 EXTREME SKIPPED）
cd "$ROOT" || exit 1
./scripts/release_up_and_verify.sh | tee /tmp/anchor_e2e_release_recover_last.out

# 5) 若 release 通过，再打 tag（脚本里已包含 release + tag）
./scripts/risk_core_tag_release.sh

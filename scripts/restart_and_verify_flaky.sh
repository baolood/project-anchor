#!/usr/bin/env bash
# When you see 405 on flaky: diagnose, rebuild backend+worker, verify backend 200,
# then manually restart Next and verify console proxy 200.
# Usage: run from project root; at 【4】restart Next in another terminal, then re-run from 【5】 or run this script again after Next is up.

set -euo pipefail

CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

echo "=============================="
echo "【0】确认当前状态（你现在是 405）"
echo "=============================="
curl -sS -i --noproxy '*' -X POST "$CONSOLE_URL/api/proxy/commands/flaky" | sed -n '1,20p' || true
echo
curl -sS -i --noproxy '*' -X POST "$BACKEND_URL/domain-commands/flaky" | sed -n '1,20p' || true
echo

echo "=============================="
echo "【1】确认代码确实存在（不存在就别重启了，先补文件）"
echo "=============================="
cd /Users/baolood/Projects/project-anchor/anchor-backend
echo "[backend] grep flaky/retry"
grep -RIn --line-number "domain-commands/flaky" app || true
grep -RIn --line-number "domain-commands/.*/retry" app || true
grep -RIn --line-number "FLAKY" app || true
echo

cd /Users/baolood/Projects/project-anchor/anchor-console
echo "[console] 确认 Next 路由文件存在"
ls -la app/api/proxy/commands/flaky/route.ts || true
ls -la app/api/proxy/commands/\[id\]/retry/route.ts || true
echo

echo "=============================="
echo "【2】重建并重启 backend+worker（确保容器跑到新代码）"
echo "=============================="
cd /Users/baolood/Projects/project-anchor/anchor-backend
docker compose down
docker compose up -d --build
docker compose ps
echo

echo "=============================="
echo "【3】验证 backend flaky 变 200（不变就 FAIL）"
echo "=============================="
B_STATUS="$(curl -sS -o /tmp/flaky_backend.out -w "%{http_code}" --noproxy '*' -X POST "$BACKEND_URL/domain-commands/flaky" || true)"
echo "BACKEND_FLAKY_HTTP_STATUS=$B_STATUS"
head -c 200 /tmp/flaky_backend.out; echo
if [ "$B_STATUS" != "200" ]; then
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=BACKEND_FLAKY_NOT_200"
  exit 1
fi
python3 - <<'PY'
import json
d=json.load(open("/tmp/flaky_backend.out"))
assert d.get("type")=="FLAKY", d
assert str(d.get("id","")).startswith("flaky-"), d
print("BACKEND_FLAKY_JSON_OK=YES")
PY
echo

echo "=============================="
echo "【4】重启 next dev（必须手动：在跑 next 的终端 Ctrl+C 后 npm run dev）"
echo "=============================="
echo "ACTION_REQUIRED=在运行 next dev 的终端按 Ctrl+C，然后在 anchor-console 目录重新执行：npm run dev"
echo "然后等看到 Ready，再回到这里继续下一步。"
echo

echo "=============================="
echo "【5】验证 console proxy flaky 变 200（不变就 FAIL）"
echo "=============================="
C_STATUS="$(curl -sS -o /tmp/flaky_console.out -w "%{http_code}" --noproxy '*' -X POST "$CONSOLE_URL/api/proxy/commands/flaky" || true)"
echo "CONSOLE_FLAKY_HTTP_STATUS=$C_STATUS"
head -c 200 /tmp/flaky_console.out; echo
if [ "$C_STATUS" != "200" ]; then
  echo "PASS_OR_FAIL=FAIL"
  echo "FAIL_REASON=CONSOLE_PROXY_FLAKY_NOT_200"
  exit 1
fi
python3 - <<'PY'
import json
d=json.load(open("/tmp/flaky_console.out"))
assert d.get("type")=="FLAKY", d
assert str(d.get("id","")).startswith("flaky-"), d
print("CONSOLE_FLAKY_JSON_OK=YES")
PY

echo
echo "PASS_OR_FAIL=PASS"
echo "FAIL_REASON="
echo "NEXT_STEP=现在直接跑 /tmp/anchor_e2e_checklist_retry_e2e.sh（你的 Step0 强预检会放行）"

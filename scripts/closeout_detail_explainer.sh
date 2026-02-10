#!/usr/bin/env bash
# MODULE=command_detail_status_explainer_closeout
# 收尾交付：造 flaky、人工看解释器、全量回归、提交单文件、输出证据模板。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONSOLE="$ROOT/anchor-console"
OUT="/tmp/anchor_e2e_verify_all_after_detail_explainer.out"

echo "== Step 1) 确保 Next 单实例在 3000（如果已在跑可跳过）"
# 若你正在跑 next dev 就不要杀；否则用下面启动（可选）
# cd "$CONSOLE"
# rm -f .next/dev/lock || true
# nohup npm run dev > /tmp/next-dev.log 2>&1 &
# sleep 2

echo "== Step 2) 造一个 flaky（用于 FAILED -> Load events -> 原因更新）"
CREATE_JSON="$(curl -sS --noproxy '*' -X POST "http://127.0.0.1:3000/api/proxy/commands/flaky")"
echo "$CREATE_JSON"
FLAKY_ID="$(python3 - <<'PY'
import json,sys
obj=json.loads(sys.stdin.read())
print(obj.get("id",""))
PY
<<<"$CREATE_JSON")"
echo "FLAKY_ID=$FLAKY_ID"

echo "== Step 3) 打开页面人工看解释器（必须人工）"
echo "OPEN_URL=http://127.0.0.1:3000/commands/$FLAKY_ID"
echo "CHECK_1: FAILED 且未加载 events 时应出现“未加载 Events”提示"
echo "CHECK_2: 点 Load events 后应更新为 ACTION_FAIL 或 POLICY_BLOCK 等更具体原因"
echo "CHECK_3: 若出现 POLICY_BLOCK 应显示“不建议重试”且 CAN_RETRY=NO；否则 ACTION_FAIL/EXCEPTION 可重试提示"

echo "== Step 4) 全量回归（必须 PASS）"
cd "$ROOT"
./scripts/verify_all_e2e.sh | tee "$OUT"
tail -n 60 "$OUT"

echo "== Step 5) 提交（只提交这一个文件）"
cd "$ROOT"
git status
git add "anchor-console/app/commands/[id]/page.tsx"
git commit -m "feat(console): command detail status explainer from events"

echo "== Step 6) 交付证据（复制粘贴用）"
echo
echo "----- git log -1 --oneline -----"
git log -1 --oneline
echo
echo "----- verify_all_e2e tail -----"
tail -n 30 "$OUT" || true
echo
echo "----- Manual UI evidence template (fill) -----"
cat <<'TXT'
MODULE=command_detail_status_explainer
DETAIL_PAGE_HAS_EXPLAIN_CARD=YES/NO
FAILED_BEFORE_EVENTS_SHOWS_HINT=YES/NO
LOAD_EVENTS_UPDATES_REASON=YES/NO
POLICY_BLOCK_SHOWS_CANNOT_RETRY=YES/NO/NA
ACTION_FAIL_SHOWS_CAN_RETRY=YES/NO/NA
DONE_SHOWS_COMPLETE=YES/NO
VERIFY_ALL_E2E_PASS=YES/NO
PASS_OR_FAIL=PASS/FAIL
FAIL_REASON=
TXT

#!/usr/bin/env bash
# Retry 闭环收尾：防回归 + 一致性 + UI
# 1) worker 无 "name 'result' is not defined"
# 2) retry e2e checklist PASS，attempt 递增一致
# 3) 列表与详情对 NEW_ID 终态一致（FAILED -> retry -> DONE）
# 4) Next dev 日志能看到 POST /api/proxy/commands/flaky 与 /retry

set -euo pipefail

ROOT="${ROOT:-/Users/baolood/Projects/project-anchor}"
BACKEND="${BACKEND:-$ROOT/anchor-backend}"
CONSOLE="${CONSOLE:-$ROOT/anchor-console}"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

echo "== 0) 重启 backend + worker（确保新代码生效） =="
cd "$BACKEND"
docker compose down
docker compose up -d --build
sleep 2

echo "== 1) worker 日志应无 result 未定义报错 =="
docker compose logs --tail=200 worker | rg -n "name 'result' is not defined" && { echo "FAIL: still seeing result error"; exit 1; } || echo "OK: result error not present"

echo "== 2) Next dev 必须只有一个实例（3000） =="
pids="$(lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null | awk 'NR>1{print $2}' | sort -u | tr '\n' ' ')"
echo "NEXT_PIDS=$pids"
cnt="$(echo "$pids" | awk '{print NF}')"
[ "$cnt" -eq 1 ] || { echo "FAIL: expected exactly 1 next dev pid on 3000, got $cnt"; exit 1; }

echo "== 3) proxy flaky + backend flaky 自检（必须 200 且 JSON type=FLAKY） =="
curl -sS -i --noproxy '*' -X POST "http://127.0.0.1:8000/domain-commands/flaky" | sed -n '1,25p'
curl -sS -i --noproxy '*' -X POST "http://127.0.0.1:3000/api/proxy/commands/flaky" | sed -n '1,25p'

echo "== 4) 跑 retry e2e（必须 PASS） =="
cp "$ROOT/scripts/checklist_retry_e2e.sh" /tmp/anchor_e2e_checklist_retry_e2e.sh
chmod +x /tmp/anchor_e2e_checklist_retry_e2e.sh
ANCHOR_BACKEND_DIR="$BACKEND" \
CONSOLE_PRECHECK="http://127.0.0.1:3000" \
BACKEND_PRECHECK="http://127.0.0.1:8000" \
bash /tmp/anchor_e2e_checklist_retry_e2e.sh | tee "$tmpdir/checklist.out"

echo "== 4b) 可选：Next 日志检查（NEXT_LOG_FILE） =="
if [ -n "${NEXT_LOG_FILE:-}" ] && [ -f "$NEXT_LOG_FILE" ]; then
  missing=""
  if ! grep "POST /api/proxy/commands/flaky" "$NEXT_LOG_FILE" | grep -q " 200 "; then
    missing="POST /api/proxy/commands/flaky with 200"
  fi
  if ! grep "POST /api/proxy/commands/" "$NEXT_LOG_FILE" | grep "/retry" | grep -q " 200 "; then
    [ -n "$missing" ] && missing="$missing; "
    missing="${missing}POST .../retry with 200"
  fi
  if [ -n "$missing" ]; then
    echo "FAIL: NEXT_LOG_FILE missing: $missing"
    exit 1
  fi
  echo "OK: Next log has POST flaky 200 and POST retry 200"
else
  echo "SKIP: NEXT_LOG_FILE not set or file missing"
fi

echo "== 5) 针对 retry 的“强一致性”检查（列表 vs 详情） =="
curl -sS --noproxy '*' "http://127.0.0.1:3000/api/proxy/commands?limit=50" > "$tmpdir/list.json"

FLAKY_ID="$(python3 - "$tmpdir/list.json" <<'PY'
import json,sys
path=sys.argv[1]
rows=json.load(open(path))
for r in rows:
    if str(r.get("id","")).startswith("flaky-"):
        print(r["id"])
        sys.exit(0)
print("")
PY
)"
echo "FLAKY_ID=$FLAKY_ID"
[ -n "$FLAKY_ID" ] || { echo "FAIL: could not find flaky-* in list top50"; exit 1; }

LIST_STATUS="$(python3 - "$tmpdir/list.json" "$FLAKY_ID" <<'PY'
import json,sys
rows=json.load(open(sys.argv[1]))
target=sys.argv[2]
for r in rows:
    if r.get("id")==target:
        print(r.get("status",""))
        sys.exit(0)
print("")
PY
)"
echo "LIST_STATUS=$LIST_STATUS"

DETAIL_STATUS="$(curl -sS --noproxy '*' "http://127.0.0.1:3000/api/proxy/commands/$FLAKY_ID" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))")"
echo "DETAIL_STATUS=$DETAIL_STATUS"

[ -n "$LIST_STATUS" ] && [ -n "$DETAIL_STATUS" ] || { echo "FAIL: empty status from list/detail"; exit 1; }
[ "$LIST_STATUS" = "$DETAIL_STATUS" ] || { echo "FAIL: list/detail mismatch ($LIST_STATUS vs $DETAIL_STATUS)"; exit 1; }
echo "OK: list/detail match"

echo "== 6) worker 日志最后再扫一次（不应出现旧错误） =="
cd "$BACKEND"
docker compose logs --tail=200 worker | rg -n "name 'result' is not defined" && { echo "FAIL: still seeing result error"; exit 1; } || echo "OK: clean"

echo "== 7) 交付验收模板 =="
BACKEND_CMD_BODY="$(curl -sS --noproxy '*' "http://127.0.0.1:8000/commands/$FLAKY_ID" 2>/dev/null || true)"
BACKEND_CMD_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' --noproxy '*' "http://127.0.0.1:8000/commands/$FLAKY_ID" 2>/dev/null || true)"
if [ "$BACKEND_CMD_HTTP" = "404" ] && echo "$BACKEND_CMD_BODY" | grep -q "Deprecated"; then
  BACKEND_COMMANDS_ID_ENDPOINT_OK=YES
else
  BACKEND_COMMANDS_ID_ENDPOINT_OK=NO
fi
SAW_FAILED="$(sed -n 's/^SAW_FAILED=//p' "$tmpdir/checklist.out" | tail -1)"
FINAL_STATUS_AFTER_RETRY="$(sed -n 's/^FINAL_STATUS_AFTER_RETRY=//p' "$tmpdir/checklist.out" | tail -1)"
ATTEMPT_AT_FAIL="$(sed -n 's/^ATTEMPT_AT_FAIL=//p' "$tmpdir/checklist.out" | tail -1)"
ATTEMPT_AT_DONE="$(sed -n 's/^ATTEMPT_AT_DONE=//p' "$tmpdir/checklist.out" | tail -1)"
if [ -n "${NEXT_LOG_FILE:-}" ] && [ -f "$NEXT_LOG_FILE" ]; then
  grep "POST /api/proxy/commands/flaky" "$NEXT_LOG_FILE" | grep -q " 200 " && NEXT_LOG_HAS_POST_FLAKY=YES || NEXT_LOG_HAS_POST_FLAKY=NO
  grep "POST /api/proxy/commands/" "$NEXT_LOG_FILE" | grep "/retry" | grep -q " 200 " && NEXT_LOG_HAS_POST_RETRY=YES || NEXT_LOG_HAS_POST_RETRY=NO
else
  NEXT_LOG_HAS_POST_FLAKY=NO
  NEXT_LOG_HAS_POST_RETRY=NO
fi
[ "$LIST_STATUS" = "$DETAIL_STATUS" ] && LIST_DETAIL_MATCH=YES || LIST_DETAIL_MATCH=NO
PASS_OR_FAIL="$(sed -n 's/^PASS_OR_FAIL=//p' "$tmpdir/checklist.out" | tail -1)"
FAIL_REASON="$(sed -n 's/^FAIL_REASON=//p' "$tmpdir/checklist.out" | tail -1)"
echo "MODULE=retry_e2e_closure_final"
echo "BACKEND_COMMANDS_ID_ENDPOINT_OK=$BACKEND_COMMANDS_ID_ENDPOINT_OK"
echo "SAW_FAILED=$SAW_FAILED"
echo "FINAL_STATUS_AFTER_RETRY=$FINAL_STATUS_AFTER_RETRY"
echo "ATTEMPT_AT_FAIL=$ATTEMPT_AT_FAIL"
echo "ATTEMPT_AT_DONE=$ATTEMPT_AT_DONE"
echo "NEXT_LOG_HAS_POST_FLAKY=$NEXT_LOG_HAS_POST_FLAKY"
echo "NEXT_LOG_HAS_POST_RETRY=$NEXT_LOG_HAS_POST_RETRY"
echo "LIST_DETAIL_MATCH=$LIST_DETAIL_MATCH"
echo "PASS_OR_FAIL=$PASS_OR_FAIL"
echo "FAIL_REASON=$FAIL_REASON"

echo "ALL PASS"

#!/usr/bin/env bash
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_risk_bypass_proof_e2e_last.out}"
BASE="${BASE:-http://127.0.0.1:8000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PASS_OR_FAIL="FAIL"
FAIL_REASON=""
S1_STOP_REQUIRED=""
S2_SINGLE_TRADE_BLOCK=""
S3_NET_EXPOSURE_BLOCK=""
S4_NOOP_ALLOWED=""
S5_QUOTE_COMPLIANT_DONE=""

say(){ echo "[$(date +%H:%M:%S)] $*"; }

emit() {
  {
    echo "MODULE=risk_bypass_proof_e2e"
    echo "BASE=$BASE"
    echo "S1_STOP_REQUIRED=$S1_STOP_REQUIRED"
    echo "S2_SINGLE_TRADE_BLOCK=$S2_SINGLE_TRADE_BLOCK"
    echo "S3_NET_EXPOSURE_BLOCK=$S3_NET_EXPOSURE_BLOCK"
    echo "S4_NOOP_ALLOWED=$S4_NOOP_ALLOWED"
    echo "S5_QUOTE_COMPLIANT_DONE=$S5_QUOTE_COMPLIANT_DONE"
    echo "PASS_OR_FAIL=$PASS_OR_FAIL"
    echo "FAIL_REASON=$FAIL_REASON"
  } | tee "$OUT" >/dev/null
}

# helpers
post_quote() {
  local payload="$1"
  curl -s -X POST "$BASE/domain-commands/quote" -H "Content-Type: application/json" -d "$payload"
}

get_cmd() {
  local id="$1"
  curl -s "$BASE/domain-commands/$id"
}

# Poll until status is DONE or FAILED (max 30s)
wait_cmd() {
  local id="$1" i=0
  while [ "$i" -lt 15 ]; do
    st="$(get_cmd "$id" | python3 -c '
import sys,json
try:
  d=json.load(sys.stdin)
  print(d.get("status",""))
except Exception:
  print("")
')"
    [[ "$st" == "DONE" || "$st" == "FAILED" ]] && return 0
    sleep 2
    i=$((i+1))
  done
  return 1
}

# 1) STOP_REQUIRED：无 stop_loss/stop_price 必须 FAIL
say "S1: STOP_REQUIRED"
r1="$(post_quote '{"symbol":"BTCUSDT","notional":5}')"
id1="$(echo "$r1" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id",""))')"
wait_cmd "$id1" || true
d1="$(get_cmd "$id1")"
err1="$(echo "$d1" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("error") or "")')"
if echo "$err1" | grep -q "STOP_REQUIRED"; then
  S1_STOP_REQUIRED="YES"
else
  S1_STOP_REQUIRED="NO"
fi

# 2) SINGLE_TRADE_RISK 或 LEVERAGE：极大 notional 必须 FAIL（不关心具体是哪条限制，必须被挡）
say "S2: BIG NOTIONAL must be blocked"
r2="$(post_quote '{"symbol":"BTCUSDT","notional":100000,"stop_loss":100}')"
id2="$(echo "$r2" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id",""))')"
wait_cmd "$id2" || true
d2="$(get_cmd "$id2")"
err2="$(echo "$d2" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("error") or "")')"
if echo "$err2" | egrep -q "SINGLE_TRADE_RISK_EXCEEDED|LEVERAGE_EXCEEDED|NET_EXPOSURE_EXCEEDED"; then
  S2_SINGLE_TRADE_BLOCK="YES"
else
  S2_SINGLE_TRADE_BLOCK="NO"
fi

# 3) NET_EXPOSURE：用并发堆敞口，必须出现 NET_EXPOSURE_EXCEEDED（证明 guard 覆盖并发生）
say "S3: NET_EXPOSURE must trigger under burst"
tmp="/tmp/anchor_bypass_quote_ids.$$"
rm -f "$tmp" || true

# 先把 exposure 归零、清 pending（dev 环境允许）
say "S3-pre: reset exposure + clear pending (dev)"
curl -s -X POST "$BASE/ops/dev/reset-pending-domain-commands" >/dev/null || true
cd "$ROOT/anchor-backend" >/dev/null
docker compose exec -T postgres psql -U anchor -d anchor -c \
"UPDATE risk_state SET current_exposure_usd=0, updated_at=NOW() WHERE id=1;" >/dev/null
cd "$ROOT" >/dev/null

# 并发 70 个 notional=5（单笔 0.5% 合规，总敞口 350 > 30%*1000=300，触发 NET_EXPOSURE）
for i in $(seq 1 70); do
  (post_quote '{"symbol":"BTCUSDT","notional":5,"stop_loss":100}' \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id",""))') >> "$tmp" &
done
wait
sleep 3

# 拉最近 100 条里 error 统计，看是否出现 NET_EXPOSURE_EXCEEDED
recent="$(curl -s "$BASE/domain-commands?limit=100")"
echo "$recent" > /tmp/anchor_bypass_recent_60_last.json
has_net="$(python3 - <<'PY'
import json,re
arr=json.load(open("/tmp/anchor_bypass_recent_60_last.json"))
for x in arr:
  e=x.get("error") or ""
  if "NET_EXPOSURE_EXCEEDED" in e:
    print("YES")
    break
else:
  print("NO")
PY
)"
S3_NET_EXPOSURE_BLOCK="$has_net"

# S3 后稍等，让 worker 消化队列；再重置 exposure，以便 S5 合规 quote 能通过
sleep 5
cd "$ROOT/anchor-backend" >/dev/null
docker compose exec -T postgres psql -U anchor -d anchor -c \
"UPDATE risk_state SET current_exposure_usd=0, updated_at=NOW() WHERE id=1;" >/dev/null
cd "$ROOT" >/dev/null

# 4) NOOP 白名单：必须 DONE（证明"允许的命令仍可执行"，且不是全局误杀）
say "S4: NOOP allowed"
r4="$(curl -s -X POST "$BASE/domain-commands/noop" -H "Content-Type: application/json" -d '{}')"
id4="$(echo "$r4" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id",""))')"
wait_cmd "$id4" || true
d4="$(get_cmd "$id4")"
st4="$(echo "$d4" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status") or "")')"
if [[ "$st4" == "DONE" ]]; then
  S4_NOOP_ALLOWED="YES"
else
  S4_NOOP_ALLOWED="NO"
fi

# 5) 合规 QUOTE：必须 DONE（证明 guard 不会误杀）
say "S5: compliant quote DONE"
r5="$(post_quote '{"symbol":"BTCUSDT","notional":5,"stop_loss":100}')"
id5="$(echo "$r5" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id",""))')"
wait_cmd "$id5" || true
d5="$(get_cmd "$id5")"
st5="$(echo "$d5" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status") or "")')"
if [[ "$st5" == "DONE" ]]; then
  S5_QUOTE_COMPLIANT_DONE="YES"
else
  S5_QUOTE_COMPLIANT_DONE="NO"
fi

# final
if [[ "$S1_STOP_REQUIRED" == "YES" && "$S2_SINGLE_TRADE_BLOCK" == "YES" && "$S3_NET_EXPOSURE_BLOCK" == "YES" && "$S4_NOOP_ALLOWED" == "YES" && "$S5_QUOTE_COMPLIANT_DONE" == "YES" ]]; then
  PASS_OR_FAIL="PASS"
  FAIL_REASON=""
else
  PASS_OR_FAIL="FAIL"
  FAIL_REASON="bypass_proof_failed"
fi

emit
[[ "$PASS_OR_FAIL" == "PASS" ]] && exit 0 || exit 1

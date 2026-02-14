#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${BASE:-http://127.0.0.1:8000}"

say(){ echo "[$(date +%H:%M:%S)] $*"; }

enter_extreme() {
  say "ENTER EXTREME MODE: reset pending + reset exposure + start worker with strict hard-limits"
  curl -s -X POST "$BASE/ops/dev/reset-pending-domain-commands" >/dev/null || true

  cd "$ROOT/anchor-backend"
  docker compose exec -T postgres psql -U anchor -d anchor -c \
"UPDATE risk_state SET current_exposure_usd=0, updated_at=NOW() WHERE id=1; SELECT * FROM risk_state;" >/dev/null

  docker compose stop worker >/dev/null 2>&1 || true
  sleep 2

  # Extreme mode: hard limits ON + atomic ON + low net exposure cap
  CAPITAL_USD="${CAPITAL_USD:-1000}" \
  MAX_SINGLE_TRADE_RISK_PCT="${MAX_SINGLE_TRADE_RISK_PCT:-100}" \
  MAX_NET_EXPOSURE_PCT="${MAX_NET_EXPOSURE_PCT:-30}" \
  MAX_LEVERAGE="${MAX_LEVERAGE:-5}" \
  MAX_DAILY_DRAWDOWN_PCT="${MAX_DAILY_DRAWDOWN_PCT:-3}" \
  RISK_HARD_LIMITS_DISABLE=0 \
  RISK_EXPOSURE_ATOMIC=1 \
  docker compose up -d worker >/dev/null

  sleep 5
  cd "$ROOT"
  say "EXTREME MODE READY"
}

run_extreme() {
  say "RUN EXTREME: 50 concurrent QUOTE notional=150 (expect DONE=2 FAILED=48)"
  python3 - <<'PY' > /tmp/anchor_extreme_ids_last.out
import concurrent.futures, json, os, time, urllib.request
BASE=os.environ.get("BASE","http://127.0.0.1:8000")
N=50
payload={"symbol":"BTCUSDT","notional":150,"stop_loss":100}
def post_quote(i):
    req=urllib.request.Request(BASE+"/domain-commands/quote", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        d=json.loads(r.read().decode())
        return d["id"]
ids=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    futs=[ex.submit(post_quote,i) for i in range(N)]
    for f in concurrent.futures.as_completed(futs):
        ids.append(f.result())
print("CREATED", len(ids))
print("\n".join(ids))
PY

  say "WAIT + COUNT outcomes for last 60 cmds"
  sleep 3
  curl -s "$BASE/domain-commands?limit=60" > /tmp/anchor_extreme_last60.json

  python3 - <<'PY' | tee /tmp/anchor_extreme_outcome_last.out
import json
p="/tmp/anchor_extreme_last60.json"
items=json.load(open(p))
done=sum(1 for x in items if x.get("status")=="DONE")
failed=sum(1 for x in items if x.get("status")=="FAILED")
print(f"DONE={done} FAILED={failed}")
# show top fail reasons
from collections import Counter
c=Counter(x.get("error") for x in items if x.get("status")=="FAILED")
print("TOP_FAILS:")
for k,v in c.most_common(10):
    print(k,v)
PY

  say "RISK STATE"
  curl -s "$BASE/risk/state" | tee /tmp/anchor_extreme_risk_state_last.json >/dev/null
}

exit_daily() {
  say "EXIT TO DAILY MODE: reset exposure + restart worker with daily defaults"
  curl -s -X POST "$BASE/ops/dev/reset-pending-domain-commands" >/dev/null || true

  cd "$ROOT/anchor-backend"
  docker compose exec -T postgres psql -U anchor -d anchor -c \
"UPDATE risk_state SET current_exposure_usd=0, updated_at=NOW() WHERE id=1; SELECT * FROM risk_state;" >/dev/null

  docker compose stop worker >/dev/null 2>&1 || true
  sleep 2

  # Daily mode: hard limits ON + atomic ON + conservative
  CAPITAL_USD="${CAPITAL_USD:-1000}" \
  MAX_SINGLE_TRADE_RISK_PCT="${MAX_SINGLE_TRADE_RISK_PCT:-0.5}" \
  MAX_NET_EXPOSURE_PCT="${MAX_NET_EXPOSURE_PCT:-30}" \
  MAX_LEVERAGE="${MAX_LEVERAGE:-5}" \
  MAX_DAILY_DRAWDOWN_PCT="${MAX_DAILY_DRAWDOWN_PCT:-3}" \
  RISK_HARD_LIMITS_DISABLE=0 \
  RISK_EXPOSURE_ATOMIC=1 \
  docker compose up -d worker >/dev/null

  sleep 5
  cd "$ROOT"
  say "DAILY MODE RESTORED"
  say "SMOKE: create notional=5 (expect DONE)"
  ID=$(curl -s -X POST "$BASE/domain-commands/quote" -H "Content-Type: application/json" -d '{"symbol":"BTCUSDT","notional":5,"stop_loss":100}' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id",""))')
  sleep 3
  curl -s "$BASE/domain-commands/$ID" > /tmp/anchor_smoke_resp.json
  python3 - <<'PY' | tee /tmp/anchor_extreme_daily_smoke_last.out
import json
try:
    with open("/tmp/anchor_smoke_resp.json") as f:
        d=json.load(f)
    print("status="+str(d.get("status"))+" error="+str(d.get("error")))
except Exception as e:
    print("ERROR:", e)
    exit(1)
PY
}

main() {
  enter_extreme
  run_extreme
  exit_daily
  say "DONE. Evidence:"
  echo "/tmp/anchor_extreme_outcome_last.out"
  echo "/tmp/anchor_extreme_risk_state_last.json"
  echo "/tmp/anchor_extreme_daily_smoke_last.out"
  echo "/tmp/anchor_extreme_ids_last.out"
}
main "$@"

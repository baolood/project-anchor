#!/usr/bin/env bash
set -e
API_KEY="${API_KEY:?Set API_KEY}"
API_SECRET="${API_SECRET:?Set API_SECRET}"

BASE="https://testnet.binancefuture.com"
SYMBOL="BTCUSDT"
SIDE="BUY"
TYPE="LIMIT"
TIF="IOC"
QTY="0.002"

# 用 mark price 做一个略高的买价，保证吃单（提高成交概率）
ts=$(date +%s000)
q1="symbol=$SYMBOL&timestamp=$ts"
s1=$(echo -n "$q1" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')
mark=$(curl -s -H "X-MBX-APIKEY: $API_KEY" "$BASE/fapi/v1/premiumIndex?$q1&signature=$s1" | jq -r '.markPrice')
price=$(python3 - <<PY
m=float("$mark")
# 买单：加 0.5%（足够"穿过"卖一）
print(f"{m*1.005:.1f}")
PY
)

ts=$(date +%s000)
query="symbol=$SYMBOL&side=$SIDE&type=$TYPE&timeInForce=$TIF&quantity=$QTY&price=$price&timestamp=$ts"
sig=$(echo -n "$query" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')

echo "markPrice=$mark  price=$price  qty=$QTY"
curl -s -H "X-MBX-APIKEY: $API_KEY" -X POST "$BASE/fapi/v1/order?$query&signature=$sig" | jq .

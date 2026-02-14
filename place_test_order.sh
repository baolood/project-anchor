#!/usr/bin/env bash
set -e

API_KEY="${API_KEY:?Set API_KEY}"
API_SECRET="${API_SECRET:?Set API_SECRET}"

BASE="https://testnet.binancefuture.com"
SYMBOL="BTCUSDT"
SIDE="BUY"
TYPE="MARKET"
# Min notional 100 USDT; 0.002 BTC ~= 200 USDT at ~100k
QUANTITY="0.002"

timestamp=$(date +%s000)
query="symbol=$SYMBOL&side=$SIDE&type=$TYPE&quantity=$QUANTITY&timestamp=$timestamp"
signature=$(echo -n "$query" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')

echo ">>> Placing test market order..."

curl -s \
  -H "X-MBX-APIKEY: $API_KEY" \
  -X POST \
  "$BASE/fapi/v1/order?$query&signature=$signature" | jq .

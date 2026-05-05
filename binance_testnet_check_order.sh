#!/usr/bin/env bash
set -euo pipefail
API_KEY="${API_KEY:?Set API_KEY}"
API_SECRET="${API_SECRET:?Set API_SECRET}"

BASE="https://testnet.binancefuture.com"
SYMBOL="BTCUSDT"
ORDER_ID="${1:?usage: $0 <orderId>}"

ts=$(date +%s000)
query="symbol=$SYMBOL&orderId=$ORDER_ID&timestamp=$ts"
sig=$(echo -n "$query" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')

curl -sS --connect-timeout 5 --max-time 20 -H "X-MBX-APIKEY: $API_KEY" "$BASE/fapi/v1/order?$query&signature=$sig" | jq .

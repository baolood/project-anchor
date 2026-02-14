#!/usr/bin/env bash
set -e
API_KEY="${API_KEY:?Set API_KEY}"
API_SECRET="${API_SECRET:?Set API_SECRET}"

BASE="https://testnet.binancefuture.com"
SYMBOL="BTCUSDT"
ORDER_ID="${1:?usage: $0 <orderId>}"

ts=$(date +%s000)
query="symbol=$SYMBOL&orderId=$ORDER_ID&timestamp=$ts"
sig=$(echo -n "$query" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')

curl -s -H "X-MBX-APIKEY: $API_KEY" -X DELETE "$BASE/fapi/v1/order?$query&signature=$sig" | jq .

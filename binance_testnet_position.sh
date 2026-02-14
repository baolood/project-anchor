#!/usr/bin/env bash
set -e
API_KEY="${API_KEY:?Set API_KEY}"
API_SECRET="${API_SECRET:?Set API_SECRET}"

BASE="https://testnet.binancefuture.com"
SYMBOL="BTCUSDT"

ts=$(date +%s000)
query="timestamp=$ts"
sig=$(echo -n "$query" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')

curl -s -H "X-MBX-APIKEY: $API_KEY" "$BASE/fapi/v2/positionRisk?$query&signature=$sig" \
| jq -c '.[] | select(.symbol=="BTCUSDT")'

#!/usr/bin/env bash
set -e

# Use env vars to avoid committing secrets. Example:
#   export API_KEY="your_key" API_SECRET="your_secret"
#   ./test_binance_testnet.sh
API_KEY="${API_KEY:?Set API_KEY}"
API_SECRET="${API_SECRET:?Set API_SECRET}"

BASE="https://testnet.binancefuture.com"

timestamp=$(date +%s000)
query="timestamp=$timestamp"
signature=$(echo -n "$query" | openssl dgst -sha256 -hmac "$API_SECRET" | sed 's/^.* //')

echo ">>> Testing account endpoint..."

curl -s \
  -H "X-MBX-APIKEY: $API_KEY" \
  "$BASE/fapi/v2/account?$query&signature=$signature" | jq .

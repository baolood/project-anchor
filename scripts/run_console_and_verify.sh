#!/usr/bin/env bash
# Ensure backend+worker up, single Next dev on 3000, quote proxy sanity, then full e2e regression.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND="$ROOT/anchor-backend"
CONSOLE="$ROOT/anchor-console"

echo "==[1/4] ensure backend+worker up =="
cd "$BACKEND"
docker compose ps
# Optional: uncomment to restart
# docker compose down
# docker compose up -d --build

echo "==[2/4] ensure single Next dev on 3000 =="
cd "$CONSOLE"
pids=$(lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null | awk 'NR>1{print $2}' | sort -u || true)
if [ -n "${pids:-}" ]; then
  echo "$pids" | xargs kill -9 || true
fi
rm -f "$CONSOLE/.next/dev/lock" || true

# Start Next in background, log to file
( cd "$CONSOLE" && nohup npm run dev > /tmp/next-dev.log 2>&1 & )

# Wait for Next ready
for i in $(seq 1 60); do
  if curl -sS --noproxy '*' -I "http://127.0.0.1:3000/" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "==[3/4] quick sanity: quote proxy should be 200 =="
curl -sS -i --noproxy '*' -X POST "http://127.0.0.1:3000/api/proxy/commands/quote" \
  -H 'content-type: application/json' \
  --data '{"symbol":"BTCUSDT","side":"BUY","notional":100}' \
  | sed -n '1,25p'

echo "==[4/4] run full regression (source of truth) =="
cd "$ROOT"
./scripts/verify_all_e2e.sh | tee /tmp/anchor_e2e_verify_all_last.out

echo
echo "===== RESULT (paste) ====="
tail -n 60 /tmp/anchor_e2e_verify_all_last.out
echo "===== NEXT LOG CHECK (optional) ====="
grep -E "POST /api/proxy/commands/quote|POST /api/proxy/commands/flaky|/retry" /tmp/next-dev.log | tail -n 20 || true

#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT/anchor-backend"

echo "== start stack =="
docker compose up -d --build postgres redis backend || true
sleep 2

echo "== health =="
curl -fsS -i http://127.0.0.1:8000/health | sed -n '1,20p'

echo "== ops audit =="
curl -sS -i "http://127.0.0.1:8000/ops/audit?limit=1" | sed -n '1,80p'

echo "PASS: server backend-only verify"

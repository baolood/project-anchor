#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${1:-anchor-backend-postgres-1}"
DB_USER="${DB_USER:-anchor}"
DB_NAME="${DB_NAME:-anchor}"

for f in $(ls "$(dirname "$0")"/*.sql | sort); do
  echo "[migrate] applying $f"
  docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$f"
done

echo "[migrate] done"

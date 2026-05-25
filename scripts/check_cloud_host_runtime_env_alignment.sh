#!/usr/bin/env bash
# Checks whether the cloud-host runtime posture is still pinned to legacy
# BINANCE_* override variables instead of the canonical TESTNET_* contract.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_cloud_host_runtime_env_alignment.sh

Reports whether the current repository/runtime posture is aligned with the
canonical real-testnet TESTNET_* contract.

This script is read-only. It does not mutate runtime, does not restart
containers, and does not authorize real testnet requests or live trading.
EOF
}

if (($# > 0)); then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "CLOUD_HOST_RUNTIME_ENV_ALIGNMENT FAIL: cannot resolve repository root" >&2
  exit 1
}

BACKEND_DIR="${ROOT}/anchor-backend"
COMPOSE_FILE="${BACKEND_DIR}/docker-compose.yml"
OVERRIDE_FILE="${BACKEND_DIR}/docker-compose.override.yml"

fail() {
  echo "CLOUD_HOST_RUNTIME_ENV_ALIGNMENT FAIL: $1" >&2
  exit 1
}

yesno() {
  if [[ "$1" == "1" ]]; then
    echo "yes"
  else
    echo "no"
  fi
}

has_pattern() {
  local file="$1"
  local pattern="$2"
  if [[ -f "$file" ]] && grep -Eq "$pattern" "$file"; then
    return 0
  fi
  return 1
}

runtime_env_lines() {
  local container="$1"
  docker inspect "$container" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null || true
}

runtime_has_pattern() {
  local text="$1"
  local pattern="$2"
  if grep -Eq "$pattern" <<<"$text"; then
    return 0
  fi
  return 1
}

[[ -f "$COMPOSE_FILE" ]] || fail "missing ${COMPOSE_FILE}"

repo_legacy_override=0
repo_canonical_override=0
repo_compose_mentions_testnet=0
runtime_backend_testnet=unknown
runtime_worker_testnet=unknown
runtime_worker_legacy=unknown

if has_pattern "$OVERRIDE_FILE" 'BINANCE_(FUTURES_BASE|API_KEY|API_SECRET)'; then
  repo_legacy_override=1
fi

if has_pattern "$OVERRIDE_FILE" 'TESTNET_(EXCHANGE_|EXECUTOR_)'; then
  repo_canonical_override=1
fi

if grep -Eq 'TESTNET_(EXCHANGE_|EXECUTOR_)' "$COMPOSE_FILE" "$OVERRIDE_FILE" 2>/dev/null; then
  repo_compose_mentions_testnet=1
fi

backend_env="$(runtime_env_lines anchor-backend-backend-1)"
worker_env="$(runtime_env_lines anchor-backend-worker-1)"

if [[ -n "$backend_env" ]]; then
  if runtime_has_pattern "$backend_env" '^TESTNET_'; then
    runtime_backend_testnet=yes
  else
    runtime_backend_testnet=no
  fi
fi

if [[ -n "$worker_env" ]]; then
  if runtime_has_pattern "$worker_env" '^TESTNET_'; then
    runtime_worker_testnet=yes
  else
    runtime_worker_testnet=no
  fi

  if runtime_has_pattern "$worker_env" '^BINANCE_'; then
    runtime_worker_legacy=yes
  else
    runtime_worker_legacy=no
  fi
fi

echo "CLOUD_HOST_RUNTIME_ENV_ALIGNMENT"
echo "REPO_LEGACY_OVERRIDE_PRESENT=$(yesno "$repo_legacy_override")"
echo "REPO_CANONICAL_TESTNET_OVERRIDE_PRESENT=$(yesno "$repo_canonical_override")"
echo "REPO_COMPOSE_MENTIONS_TESTNET=$(yesno "$repo_compose_mentions_testnet")"
echo "RUNTIME_BACKEND_TESTNET_ENV_PRESENT=${runtime_backend_testnet}"
echo "RUNTIME_WORKER_TESTNET_ENV_PRESENT=${runtime_worker_testnet}"
echo "RUNTIME_WORKER_LEGACY_BINANCE_ENV_PRESENT=${runtime_worker_legacy}"

reasons=()

if ((repo_legacy_override == 1)); then
  reasons+=("legacy_override_present")
fi

if [[ "$runtime_backend_testnet" == "no" ]]; then
  reasons+=("backend_testnet_missing")
fi

if [[ "$runtime_worker_testnet" == "no" ]]; then
  reasons+=("worker_testnet_missing")
fi

if [[ "$runtime_worker_legacy" == "yes" ]]; then
  reasons+=("worker_legacy_binance_present")
fi

if [[ "$runtime_backend_testnet" == "unknown" || "$runtime_worker_testnet" == "unknown" || "$runtime_worker_legacy" == "unknown" ]]; then
  reasons+=("runtime_unverified")
fi

if ((${#reasons[@]} > 0)); then
  echo "CLOUD_HOST_RUNTIME_ENV_ALIGNMENT BLOCKED: ${reasons[*]}"
  exit 1
fi

echo "CLOUD_HOST_RUNTIME_ENV_ALIGNMENT PASS: canonical_testnet_runtime_aligned"

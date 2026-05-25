#!/usr/bin/env bash
# Validates that the review-artifact directory keeps synthetic examples and
# future first-controlled-send actual artifacts clearly separated.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_first_controlled_send_transition_state.sh

Scans docs/reviews/real_testnet/ and checks:
- legacy FIRST_REAL_REQUEST example files remain obviously synthetic
- no FIRST_CONTROLLED_SEND file uses example wording or example-style suffixes
- no review artifact filename leaks secrets

This script validates transition-state hygiene only.
It does not authorize a real controlled send or live trading.
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
  echo "FIRST_CONTROLLED_SEND_TRANSITION_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

DIR="${ROOT}/docs/reviews/real_testnet"
[[ -d "$DIR" ]] || {
  echo "FIRST_CONTROLLED_SEND_TRANSITION_CHECK FAIL: missing review artifact directory" >&2
  exit 1
}

fail() {
  echo "FIRST_CONTROLLED_SEND_TRANSITION_CHECK FAIL: $1" >&2
  exit 1
}

legacy_found=0
actual_found=0

while IFS= read -r file; do
  base="$(basename "$file")"

  if grep -Eqi 'api key|api secret|raw auth header|request signature|plaintext credential|secret:' "$file"; then
    fail "secret-bearing marker found in ${base}"
  fi

  case "$base" in
    FIRST_REAL_REQUEST_*.md)
      legacy_found=1
      if [[ ! "$base" =~ example-(pass|fail|blocked) ]]; then
        fail "legacy FIRST_REAL_REQUEST artifact must remain obviously synthetic: ${base}"
      fi
      if ! grep -Eqi 'synthetic example|example artifact|style reference only|not evidence of a real request' "$file"; then
        fail "legacy FIRST_REAL_REQUEST example lacks explicit synthetic marker: ${base}"
      fi
      ;;
    FIRST_CONTROLLED_SEND_*.md)
      actual_found=1
      if [[ "$base" =~ example-(pass|fail|blocked) ]]; then
        fail "FIRST_CONTROLLED_SEND artifact must not use example-style suffixes: ${base}"
      fi
      if grep -Eqi 'synthetic example|example only|style reference only|not evidence of a real request' "$file"; then
        fail "FIRST_CONTROLLED_SEND artifact still contains synthetic/example wording: ${base}"
      fi
      ;;
  esac
done < <(find "$DIR" -maxdepth 1 -type f \( -name 'FIRST_REAL_REQUEST_*.md' -o -name 'FIRST_CONTROLLED_SEND_*.md' \) | sort)

if ((legacy_found == 0 && actual_found == 0)); then
  fail "no review artifacts found under docs/reviews/real_testnet/"
fi

echo "FIRST_CONTROLLED_SEND_TRANSITION_CHECK PASS: legacy_examples=${legacy_found} actual_artifacts=${actual_found}"

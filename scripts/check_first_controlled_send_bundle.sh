#!/usr/bin/env bash
# Validates whether the repo currently has one reviewable first-controlled-send
# filled artifact bundle, using the narrower actual-artifact and real-fill checks.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_first_controlled_send_bundle.sh [artifact-path]

Without an argument:
- scans docs/reviews/real_testnet/ for FIRST_CONTROLLED_SEND_*.md
- reports BLOCKED when no actual filled artifact exists yet
- requires exactly one candidate unless an explicit path is supplied

With an argument:
- validates the given candidate artifact as a first-controlled-send bundle entry

Checks:
- actual-artifact check passes
- real-fill check passes
- bundle-level review fields are present

This script does not authorize a real controlled send or live trading.
EOF
}

if (($# > 1)); then
  usage >&2
  exit 2
fi

if (($# == 1)) && [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "FIRST_CONTROLLED_SEND_BUNDLE_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

ARTIFACT_DIR="${ROOT}/docs/reviews/real_testnet"
ACTUAL_CHECK="${ROOT}/scripts/check_first_controlled_send_actual_artifact.sh"
REAL_FILL_CHECK="${ROOT}/scripts/check_first_controlled_send_real_fill.sh"

fail() {
  echo "FIRST_CONTROLLED_SEND_BUNDLE_CHECK FAIL: $1" >&2
  exit 1
}

block() {
  echo "FIRST_CONTROLLED_SEND_BUNDLE_CHECK BLOCKED: $1" >&2
  exit 1
}

resolve_artifact() {
  local input="$1"
  case "$input" in
    /*) printf '%s\n' "$input" ;;
    *) printf '%s/%s\n' "$ROOT" "$input" ;;
  esac
}

if (($# == 1)); then
  ARTIFACT="$(resolve_artifact "$1")"
else
  matches=()
  while IFS= read -r line; do
    matches+=("$line")
  done < <(find "$ARTIFACT_DIR" -maxdepth 1 -type f -name 'FIRST_CONTROLLED_SEND_*.md' | sort)
  if ((${#matches[@]} == 0)); then
    block "no FIRST_CONTROLLED_SEND_*.md artifact exists yet under docs/reviews/real_testnet/"
  fi
  if ((${#matches[@]} > 1)); then
    fail "multiple FIRST_CONTROLLED_SEND artifacts found; pass one explicit path"
  fi
  ARTIFACT="${matches[0]}"
fi

[[ -f "$ARTIFACT" ]] || fail "missing file: $ARTIFACT"

"$ACTUAL_CHECK" "$ARTIFACT" >/dev/null
"$REAL_FILL_CHECK" "$ARTIFACT" >/dev/null

line_has_value() {
  local key="$1"
  grep -Eq "^${key}:[[:space:]]*[^[:space:]].*$" "$ARTIFACT"
}

line_has_any_value() {
  local keys=("$@")
  local key
  for key in "${keys[@]}"; do
    if line_has_value "$key"; then
      return 0
    fi
  done
  return 1
}

line_has_any_value "external_request_status" || fail "missing external_request_status"

if ! line_has_any_value "retreat_required"; then
  fail "missing retreat_required"
fi

if ! line_has_any_value "notes"; then
  fail "missing notes"
fi

base="$(basename "$ARTIFACT")"
echo "FIRST_CONTROLLED_SEND_BUNDLE_CHECK PASS: ${base}"

#!/usr/bin/env bash
# Validates whether a real first-controlled-send filled artifact exists and
# carries the minimum non-synthetic fields expected by the real-fill layer.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_first_controlled_send_real_fill.sh [artifact-path]

Without an argument:
- scans docs/reviews/real_testnet/ for FIRST_CONTROLLED_SEND_*.md
- fails BLOCKED when no actual artifact exists yet
- prefers the newest candidate unless an explicit path is supplied

With an argument:
- validates the given candidate filled artifact

Checks:
- actual-artifact form passes
- minimal real-fill fields are present
- obvious guesswork wording is absent

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
  echo "FIRST_CONTROLLED_SEND_REAL_FILL_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

ARTIFACT_DIR="${ROOT}/docs/reviews/real_testnet"
ARTIFACT_CHECK="${ROOT}/scripts/check_first_controlled_send_actual_artifact.sh"

fail() {
  echo "FIRST_CONTROLLED_SEND_REAL_FILL_CHECK FAIL: $1" >&2
  exit 1
}

block() {
  echo "FIRST_CONTROLLED_SEND_REAL_FILL_CHECK BLOCKED: $1" >&2
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
  # Multiple bounded artifacts may exist over time. Default to the newest
  # candidate so CI can validate the current reviewed posture without forcing
  # historical artifacts out of the repository.
  ARTIFACT="${matches[$((${#matches[@]} - 1))]}"
fi

[[ -f "$ARTIFACT" ]] || fail "missing file: $ARTIFACT"

"$ARTIFACT_CHECK" "$ARTIFACT" >/dev/null

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

line_has_any_value "final_command_state" "command_state" || fail "missing final command state"
line_has_any_value "normalized_family" "final_family" || fail "missing normalized family"

if grep -Eqi 'looks like|probably|maybe|appears to|seems like|guessed from memory' "$ARTIFACT"; then
  fail "artifact contains guesswork wording"
fi

if grep -Eq 'NOT_COLLECTED' "$ARTIFACT"; then
  if ! grep -Eq 'NOT_COLLECTED.*(reason|because|due to|unreachable|missing|not available)' "$ARTIFACT"; then
    fail "NOT_COLLECTED appears without an attached reason"
  fi
fi

base="$(basename "$ARTIFACT")"
echo "FIRST_CONTROLLED_SEND_REAL_FILL_CHECK PASS: ${base}"

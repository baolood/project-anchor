#!/usr/bin/env bash
# Reports whether a real first-controlled-send review pack is present and, if so,
# validates it through the existing bundle checker.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_first_controlled_send_review_pack_presence.sh

Scans docs/reviews/real_testnet/ for FIRST_CONTROLLED_SEND_*.md.

Outcomes:
- BLOCKED when no actual first-controlled-send review pack exists yet
- PASS when the newest actual review pack exists and passes the bundle check

This script does not authorize a real controlled send or live trading.
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
  echo "FIRST_CONTROLLED_SEND_REVIEW_PACK_CHECK FAIL: cannot resolve repository root" >&2
  exit 1
}

DIR="${ROOT}/docs/reviews/real_testnet"
BUNDLE_CHECK="${ROOT}/scripts/check_first_controlled_send_bundle.sh"

fail() {
  echo "FIRST_CONTROLLED_SEND_REVIEW_PACK_CHECK FAIL: $1" >&2
  exit 1
}

block() {
  echo "FIRST_CONTROLLED_SEND_REVIEW_PACK_CHECK BLOCKED: $1" >&2
  exit 1
}

matches=()
while IFS= read -r line; do
  matches+=("$line")
done < <(find "$DIR" -maxdepth 1 -type f -name 'FIRST_CONTROLLED_SEND_*.md' | sort)

if ((${#matches[@]} == 0)); then
  block "no actual FIRST_CONTROLLED_SEND review pack exists yet"
fi

# Multiple bounded review packs may accumulate historically. Validate the
# newest one as the current project-facing reviewed pack.
artifact="${matches[$((${#matches[@]} - 1))]}"
"$BUNDLE_CHECK" "$artifact" >/dev/null

echo "FIRST_CONTROLLED_SEND_REVIEW_PACK_CHECK PASS: $(basename "$artifact")"

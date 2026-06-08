#!/usr/bin/env bash
# Summarizes the current first-controlled-send evidence gate state.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/check_first_controlled_send_gate_summary.sh

Runs the first-controlled-send validation stack and prints one bounded status:
- synthetic_only
- actual_missing
- review_pack_missing
- ready_for_real_review
- reviewed_pass

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
  echo "FIRST_CONTROLLED_SEND_GATE_SUMMARY FAIL: cannot resolve repository root" >&2
  exit 1
}

TRANSITION_CHECK="${ROOT}/scripts/check_first_controlled_send_transition_state.sh"
ACTUAL_CHECK="${ROOT}/scripts/check_first_controlled_send_actual_artifact.sh"
REAL_FILL_CHECK="${ROOT}/scripts/check_first_controlled_send_real_fill.sh"
REVIEW_PACK_CHECK="${ROOT}/scripts/check_first_controlled_send_review_pack_presence.sh"
ARTIFACT_DIR="${ROOT}/docs/reviews/real_testnet"

fail() {
  echo "FIRST_CONTROLLED_SEND_GATE_SUMMARY FAIL: $1" >&2
  exit 1
}

if ! "$TRANSITION_CHECK" >/dev/null 2>&1; then
  fail "transition-state check failed"
fi

matches=()
while IFS= read -r line; do
  matches+=("$line")
done < <(find "$ARTIFACT_DIR" -maxdepth 1 -type f -name 'FIRST_CONTROLLED_SEND_*.md' | sort)

if ((${#matches[@]} == 0)); then
  echo "FIRST_CONTROLLED_SEND_GATE_SUMMARY BLOCKED: synthetic_only actual_missing review_pack_missing"
  exit 1
fi

# Multiple bounded artifacts may exist over time. Use the newest artifact as
# the current event under review.
artifact="${matches[$((${#matches[@]} - 1))]}"

if ! "$ACTUAL_CHECK" "$artifact" >/dev/null 2>&1; then
  fail "actual-artifact check failed for $(basename "$artifact")"
fi

if ! "$REAL_FILL_CHECK" "$artifact" >/dev/null 2>&1; then
  echo "FIRST_CONTROLLED_SEND_GATE_SUMMARY BLOCKED: actual_present review_pack_incomplete"
  exit 1
fi

if ! "$REVIEW_PACK_CHECK" >/dev/null 2>&1; then
  echo "FIRST_CONTROLLED_SEND_GATE_SUMMARY BLOCKED: actual_present real_fill_present review_pack_missing"
  exit 1
fi

if grep -Eq '^final_result_label:[[:space:]]*PASS$' "$artifact" \
  && grep -Eq '^final_command_state:[[:space:]]*DONE$' "$artifact"; then
  echo "FIRST_CONTROLLED_SEND_GATE_SUMMARY PASS: reviewed_pass $(basename "$artifact")"
  exit 0
fi

echo "FIRST_CONTROLLED_SEND_GATE_SUMMARY PASS: ready_for_real_review $(basename "$artifact")"

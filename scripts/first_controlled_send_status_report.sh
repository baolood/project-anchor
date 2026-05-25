#!/usr/bin/env bash
# Emits a small machine-readable status snapshot for first-controlled-send readiness.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "FIRST_CONTROLLED_SEND_STATUS FAIL: cannot resolve repository root" >&2
  exit 1
}

SUMMARY_SCRIPT="${ROOT}/scripts/check_first_controlled_send_gate_summary.sh"
ARTIFACT_DIR="${ROOT}/docs/reviews/real_testnet"

OUT_FILE="${OUT_FILE:-}"
CHECK_DOMAIN_GATE=0

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "FIRST_CONTROLLED_SEND_STATUS FAIL: ${opt} requires a value." >&2
    exit 2
  fi
}

while (($# > 0)); do
  case "$1" in
    --out)
      require_value "--out" "${2:-}"
      OUT_FILE="${2:-}"
      shift 2
      ;;
    --check-domain-gate)
      CHECK_DOMAIN_GATE=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/first_controlled_send_status_report.sh [--out <path>] [--check-domain-gate]

Options:
  --out <path>  Write the report to a file (stdout always prints).
  --check-domain-gate  Exit non-zero unless DOMAIN_WORTH_BUYING=yes.

Fields:
  STATE                  synthetic_only / actual_missing / review_pack_missing / ready_for_real_review
  LEGACY_EXAMPLES        count of FIRST_REAL_REQUEST synthetic examples
  ACTUAL_ARTIFACTS       count of FIRST_CONTROLLED_SEND actual artifacts
  DOMAIN_WORTH_BUYING    yes/no
  EXTERNAL_SHOWCASE_READY yes/no

This report does not authorize a real controlled send or live trading.
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Run with --help for usage." >&2
      exit 2
      ;;
  esac
done

summary_output=""
summary_exit=0
if ! summary_output="$("$SUMMARY_SCRIPT" 2>&1)"; then
  summary_exit=$?
fi

state="unknown"
if grep -q 'ready_for_real_review' <<<"$summary_output"; then
  state="ready_for_real_review"
elif grep -q 'actual_present real_fill_present review_pack_missing' <<<"$summary_output"; then
  state="review_pack_missing"
elif grep -q 'actual_present review_pack_incomplete' <<<"$summary_output"; then
  state="actual_missing"
elif grep -q 'synthetic_only actual_missing review_pack_missing' <<<"$summary_output"; then
  state="synthetic_only"
elif [[ $summary_exit -ne 0 ]]; then
  echo "$summary_output" >&2
  echo "FIRST_CONTROLLED_SEND_STATUS FAIL: could not classify gate-summary output" >&2
  exit 1
fi

legacy_examples=0
actual_artifacts=0
while IFS= read -r line; do
  case "$(basename "$line")" in
    FIRST_REAL_REQUEST_*.md) legacy_examples=$((legacy_examples + 1)) ;;
    FIRST_CONTROLLED_SEND_*.md) actual_artifacts=$((actual_artifacts + 1)) ;;
  esac
done < <(find "$ARTIFACT_DIR" -maxdepth 1 -type f \( -name 'FIRST_REAL_REQUEST_*.md' -o -name 'FIRST_CONTROLLED_SEND_*.md' \) | sort)

domain_worth_buying="no"
external_showcase_ready="no"
if [[ "$state" == "ready_for_real_review" ]]; then
  domain_worth_buying="yes"
  external_showcase_ready="yes"
fi

report="$(cat <<EOF
FIRST_CONTROLLED_SEND_STATUS_REPORT
STATE=${state}
LEGACY_EXAMPLES=${legacy_examples}
ACTUAL_ARTIFACTS=${actual_artifacts}
DOMAIN_WORTH_BUYING=${domain_worth_buying}
EXTERNAL_SHOWCASE_READY=${external_showcase_ready}
EOF
)"

echo "$report"

if [[ -n "$OUT_FILE" ]]; then
  if [[ "${OUT_FILE}" == */ ]]; then
    echo "FIRST_CONTROLLED_SEND_STATUS FAIL: --out expects a file path, got directory-like path: ${OUT_FILE}" >&2
    exit 2
  fi
  if [[ -d "${OUT_FILE}" ]]; then
    echo "FIRST_CONTROLLED_SEND_STATUS FAIL: --out expects a file path, got directory: ${OUT_FILE}" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%s\n' "$report" > "$OUT_FILE"
  echo "WROTE_REPORT=$OUT_FILE"
fi

if ((CHECK_DOMAIN_GATE == 1)); then
  if [[ "$domain_worth_buying" != "yes" ]]; then
    echo "FIRST_CONTROLLED_SEND_DOMAIN_GATE BLOCKED: DOMAIN_WORTH_BUYING=${domain_worth_buying}" >&2
    exit 1
  fi
  echo "FIRST_CONTROLLED_SEND_DOMAIN_GATE PASS: DOMAIN_WORTH_BUYING=yes"
fi

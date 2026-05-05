#!/usr/bin/env bash
# Quick helper: inspect recent local-box-baseline workflow runs.
set -euo pipefail

WORKFLOW_FILE="${WORKFLOW_FILE:-local-box-baseline.yml}"
LIMIT="${LIMIT:-10}"
BRANCH="${BRANCH:-}"
CANCELLED_ONLY=0
LATEST_ONLY=0
SUMMARY=0

while (($# > 0)); do
  case "$1" in
    --workflow)
      WORKFLOW_FILE="${2:-}"
      shift 2
      ;;
    --limit)
      LIMIT="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH="${2:-}"
      shift 2
      ;;
    --cancelled-only)
      CANCELLED_ONLY=1
      shift
      ;;
    --latest-only)
      LATEST_ONLY=1
      shift
      ;;
    --summary)
      SUMMARY=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/check_local_box_ci_runs.sh [--workflow <file>] [--limit <n>] [--branch <name>] [--cancelled-only] [--latest-only] [--summary]

Options:
  --workflow  Workflow file name (default: local-box-baseline.yml)
  --limit     Number of runs to fetch (default: 10)
  --branch    Filter output to one branch/ref name
  --cancelled-only  Show only cancelled runs (useful for concurrency checks)
  --latest-only     Keep only newest run per branch from the fetched set
  --summary         Print status/conclusion counts for filtered rows
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

if ! command -v gh >/dev/null 2>&1; then
  echo "CI_RUNS_CHECK FAIL: gh CLI not found." >&2
  echo "Install GitHub CLI and authenticate (gh auth login)." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "CI_RUNS_CHECK FAIL: gh CLI not authenticated." >&2
  echo "Run: gh auth login" >&2
  exit 1
fi

echo "== Recent runs: ${WORKFLOW_FILE} (limit=${LIMIT}) =="
rows="$(gh run list --workflow "${WORKFLOW_FILE}" --limit "${LIMIT}" \
  --json databaseId,headBranch,status,conclusion,event,displayTitle,createdAt,updatedAt \
  --jq '.[] | "\(.databaseId)\t\(.headBranch)\t\(.status)\t\(.conclusion // "n/a")\t\(.event)\t\(.displayTitle)"')"

output="$rows"
if [[ -n "${BRANCH}" ]]; then
  echo "(filtered branch=${BRANCH})"
  output="$(printf '%s\n' "$output" | awk -F '\t' -v b="$BRANCH" '$2==b {print}')"
fi
if [[ "$CANCELLED_ONLY" -eq 1 ]]; then
  echo "(filtered cancelled-only)"
  output="$(printf '%s\n' "$output" | awk -F '\t' '$4=="cancelled" {print}')"
fi
if [[ "$LATEST_ONLY" -eq 1 ]]; then
  echo "(filtered latest-only per branch)"
  output="$(printf '%s\n' "$output" | awk -F '\t' '!seen[$2]++')"
fi
printf '%s\n' "$output"

if [[ "$SUMMARY" -eq 1 ]]; then
  echo
  echo "== Summary =="
  printf '%s\n' "$output" | awk -F '\t' '
    NF>=4 {
      status[$3]++
      conclusion[$4]++
      total++
    }
    END {
      print "total_rows\t" (total+0)
      for (k in status) print "status_" k "\t" status[k]
      for (k in conclusion) print "conclusion_" k "\t" conclusion[k]
    }'
fi

echo
echo "Tip: under concurrency cancel-in-progress, older runs on the same branch may show cancelled."
echo "Use the newest run on the branch/ref as source of truth."

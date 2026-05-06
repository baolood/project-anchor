#!/usr/bin/env bash
# Inspect recent local-box-baseline (and other) workflow runs via gh.
# Repo README.md → "CI" lists job roles and local triage order; this script lists/filter gates runs.
set -euo pipefail

WORKFLOW_FILE="${WORKFLOW_FILE:-local-box-baseline.yml}"
LIMIT="${LIMIT:-10}"
BRANCH="${BRANCH:-}"
CANCELLED_ONLY=0
LATEST_ONLY=0
SUMMARY=0
REQUIRE_LATEST_SUCCESS=0
QUIET=0
JSON_OUTPUT=0
FAIL_ON_CANCELLED=0

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
    --require-latest-success)
      REQUIRE_LATEST_SUCCESS=1
      shift
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    --json)
      JSON_OUTPUT=1
      shift
      ;;
    --fail-on-cancelled)
      FAIL_ON_CANCELLED=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/check_local_box_ci_runs.sh [--workflow <file>] [--limit <n>] [--branch <name>] [--cancelled-only] [--latest-only] [--summary] [--require-latest-success] [--quiet] [--json] [--fail-on-cancelled]

Options:
  --workflow  Workflow file name (default: local-box-baseline.yml)
  --limit     Number of runs to fetch (default: 10)
  --branch    Filter output to one branch/ref name
  --cancelled-only  Show only cancelled runs (useful for concurrency checks)
  --latest-only     Keep only newest run per branch from the fetched set
  --summary         Print status/conclusion counts for filtered rows
  --require-latest-success  Exit non-zero unless latest run on --branch is successful
  --quiet           Suppress table/tips; useful with --require-latest-success in scripts
  --json            Emit filtered rows as JSON (for automation)
  --fail-on-cancelled  Exit non-zero if any filtered row has conclusion=cancelled

See also: README.md (section "CI") for workflow jobs and reproducing failures locally.
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

if [[ "$REQUIRE_LATEST_SUCCESS" -eq 1 && -z "${BRANCH}" ]]; then
  echo "CI_RUNS_CHECK FAIL: --require-latest-success requires --branch <name>." >&2
  exit 2
fi
if [[ "$LIMIT" =~ ^[0-9]+$ ]] && [[ "$LIMIT" -gt 0 ]]; then
  :
else
  echo "CI_RUNS_CHECK FAIL: --limit must be a positive integer." >&2
  exit 2
fi

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

if [[ "$QUIET" -eq 0 ]]; then
  echo "== Recent runs: ${WORKFLOW_FILE} (limit=${LIMIT}) =="
fi
rows="$(gh run list --workflow "${WORKFLOW_FILE}" --limit "${LIMIT}" \
  --json databaseId,headBranch,status,conclusion,event,displayTitle,createdAt,updatedAt \
  --jq '.[] | "\(.databaseId)\t\(.headBranch)\t\(.status)\t\(.conclusion // "n/a")\t\(.event)\t\(.displayTitle)"')"

output="$rows"
if [[ -n "${BRANCH}" ]]; then
  [[ "$QUIET" -eq 0 ]] && echo "(filtered branch=${BRANCH})"
  output="$(printf '%s\n' "$output" | awk -F '\t' -v b="$BRANCH" '$2==b {print}')"
fi
if [[ "$CANCELLED_ONLY" -eq 1 ]]; then
  [[ "$QUIET" -eq 0 ]] && echo "(filtered cancelled-only)"
  output="$(printf '%s\n' "$output" | awk -F '\t' '$4=="cancelled" {print}')"
fi
if [[ "$LATEST_ONLY" -eq 1 ]]; then
  [[ "$QUIET" -eq 0 ]] && echo "(filtered latest-only per branch)"
  output="$(printf '%s\n' "$output" | awk -F '\t' '!seen[$2]++')"
fi
if [[ "$JSON_OUTPUT" -eq 1 ]]; then
  printf '%s\n' "$output" | python3 - <<'PY'
import json
import sys

rows = []
for raw in sys.stdin:
    raw = raw.rstrip("\n")
    if not raw:
        continue
    parts = raw.split("\t")
    if len(parts) < 6:
        continue
    rows.append(
        {
            "databaseId": parts[0],
            "headBranch": parts[1],
            "status": parts[2],
            "conclusion": parts[3],
            "event": parts[4],
            "displayTitle": parts[5],
        }
    )
print(json.dumps(rows, ensure_ascii=True))
PY
elif [[ "$QUIET" -eq 0 ]]; then
  printf '%s\n' "$output"
fi

if [[ "$SUMMARY" -eq 1 && "$JSON_OUTPUT" -eq 0 ]]; then
  [[ "$QUIET" -eq 0 ]] && echo && echo "== Summary =="
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

if [[ "$REQUIRE_LATEST_SUCCESS" -eq 1 ]]; then
  latest_line="$(printf '%s\n' "$rows" | awk -F '\t' -v b="$BRANCH" '$2==b {print; exit}')"
  if [[ -z "${latest_line}" ]]; then
    echo "CI_RUNS_CHECK FAIL: no runs found for branch=${BRANCH}" >&2
    exit 1
  fi
  latest_status="$(printf '%s\n' "$latest_line" | awk -F '\t' '{print $3}')"
  latest_conclusion="$(printf '%s\n' "$latest_line" | awk -F '\t' '{print $4}')"
  if [[ "$latest_status" != "completed" || "$latest_conclusion" != "success" ]]; then
    echo "CI_RUNS_CHECK FAIL: latest run for branch=${BRANCH} is status=${latest_status}, conclusion=${latest_conclusion}" >&2
    exit 1
  fi
  [[ "$QUIET" -eq 0 ]] && echo "CI_RUNS_CHECK PASS: latest run for branch=${BRANCH} is successful"
fi

if [[ "$FAIL_ON_CANCELLED" -eq 1 ]]; then
  cancelled_count="$(printf '%s\n' "$output" | awk -F '\t' '$4=="cancelled" {n++} END {print n+0}')"
  if [[ "$cancelled_count" -gt 0 ]]; then
    echo "CI_RUNS_CHECK FAIL: found ${cancelled_count} cancelled run(s) in filtered output" >&2
    exit 1
  fi
  [[ "$QUIET" -eq 0 ]] && echo "CI_RUNS_CHECK PASS: no cancelled runs in filtered output"
fi

if [[ "$QUIET" -eq 0 && "$JSON_OUTPUT" -eq 0 ]]; then
  echo
  echo "Tip: under concurrency cancel-in-progress, older runs on the same branch may show cancelled."
  echo "Use the newest run on the branch/ref as source of truth."
fi

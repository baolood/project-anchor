#!/usr/bin/env bash
# Inspect recent local-box-baseline (and other) workflow runs via gh.
# Repo README.md → "CI" lists job roles and local triage order; this script lists/filter gates runs.
set -euo pipefail

WORKFLOW_FILE="${WORKFLOW_FILE:-local-box-baseline.yml}"
LIMIT="${LIMIT:-10}"
BRANCH="${BRANCH:-}"
CANCELLED_ONLY=0
FAILED_ONLY=0
LATEST_ONLY=0
SUMMARY=0
REQUIRE_LATEST_SUCCESS=0
QUIET=0
JSON_OUTPUT=0
FAIL_ON_CANCELLED=0
FAIL_ON_FAILED=0
FAIL_ON_INCOMPLETE=0
FAIL_ON_EMPTY=0
GATE_STRICT=0

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "CI_RUNS_CHECK FAIL: ${opt} requires a value." >&2
    exit 2
  fi
}

while (($# > 0)); do
  case "$1" in
    --workflow)
      require_value "--workflow" "${2:-}"
      WORKFLOW_FILE="${2:-}"
      shift 2
      ;;
    --limit)
      require_value "--limit" "${2:-}"
      LIMIT="${2:-}"
      shift 2
      ;;
    --branch)
      require_value "--branch" "${2:-}"
      BRANCH="${2:-}"
      shift 2
      ;;
    --cancelled-only|--canceled-only)
      CANCELLED_ONLY=1
      shift
      ;;
    --failed-only)
      FAILED_ONLY=1
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
    --fail-on-cancelled|--fail-on-canceled)
      FAIL_ON_CANCELLED=1
      shift
      ;;
    --fail-on-failed|--fail-on-non-success)
      FAIL_ON_FAILED=1
      shift
      ;;
    --fail-on-incomplete|--fail-on-non-completed)
      FAIL_ON_INCOMPLETE=1
      shift
      ;;
    --fail-on-empty)
      FAIL_ON_EMPTY=1
      shift
      ;;
    --gate-strict|--strict)
      GATE_STRICT=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/check_local_box_ci_runs.sh [--workflow <file>] [--limit <n>] [--branch <name>] [--cancelled-only|--canceled-only] [--failed-only] [--latest-only] [--summary] [--require-latest-success] [--quiet] [--json] [--fail-on-cancelled|--fail-on-canceled] [--fail-on-failed|--fail-on-non-success] [--fail-on-incomplete|--fail-on-non-completed] [--fail-on-empty] [--gate-strict|--strict]

Options:
  --workflow  Workflow file name (default: local-box-baseline.yml)
  --limit     Number of runs to fetch (default: 10)
  --branch    Pass through to gh as run list --branch (recommended for ordering + --require-latest-success)
  --cancelled-only, --canceled-only
                  Show only cancelled runs (useful for concurrency checks)
  --failed-only     Show only completed non-success, non-cancelled runs (excludes --cancelled-only|--canceled-only)
  --latest-only     Keep only newest run per branch from the fetched set
  --summary         Print status/conclusion counts for filtered rows
  --require-latest-success  Exit non-zero unless latest run on --branch is successful
  --quiet           Suppress table/tips; useful with --require-latest-success in scripts
  --json            Emit filtered rows as JSON (for automation)
  --fail-on-cancelled, --fail-on-canceled
                  Exit non-zero if any filtered row has conclusion=cancelled
  --fail-on-failed, --fail-on-non-success
                  Exit non-zero if any filtered row is completed and non-success/non-cancelled
  --fail-on-incomplete, --fail-on-non-completed
                  Exit non-zero if any filtered row has status other than completed
  --fail-on-empty    Exit non-zero if filtered output has zero rows
  --gate-strict, --strict
                  Convenience preset: --latest-only --fail-on-cancelled --fail-on-failed --fail-on-incomplete --fail-on-empty
                     (requires --branch; mutually exclusive with --cancelled-only / --canceled-only / --failed-only)

See also: README.md (section "CI") for workflow jobs and reproducing failures locally.
For per-job wall-clock caps see .github/workflows/local-box-baseline.yml (timeout-minutes).

Examples:
  ./scripts/check_local_box_ci_runs.sh --branch main --limit 20
  ./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-failed   # alias: --fail-on-non-success
  ./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-incomplete # alias: --fail-on-non-completed
  ./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-empty
  ./scripts/check_local_box_ci_runs.sh --branch main --gate-strict --quiet
  ./scripts/check_local_box_ci_runs.sh --branch main --strict --quiet
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
if [[ "$CANCELLED_ONLY" -eq 1 && "$FAILED_ONLY" -eq 1 ]]; then
  echo "CI_RUNS_CHECK FAIL: --cancelled-only and --failed-only are mutually exclusive." >&2
  exit 2
fi
if [[ "$GATE_STRICT" -eq 1 ]]; then
  if [[ -z "${BRANCH}" ]]; then
    echo "CI_RUNS_CHECK FAIL: --gate-strict/--strict requires --branch <name>." >&2
    exit 2
  fi
  if [[ "$CANCELLED_ONLY" -eq 1 || "$FAILED_ONLY" -eq 1 ]]; then
    echo "CI_RUNS_CHECK FAIL: --gate-strict/--strict cannot be combined with --cancelled-only / --canceled-only / --failed-only." >&2
    exit 2
  fi
  LATEST_ONLY=1
  FAIL_ON_CANCELLED=1
  FAIL_ON_FAILED=1
  FAIL_ON_INCOMPLETE=1
  FAIL_ON_EMPTY=1
  [[ "$QUIET" -eq 0 ]] && echo "(preset --gate-strict/--strict: latest-only + fail-on-cancelled + fail-on-failed + fail-on-incomplete + fail-on-empty)"
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
  echo "Install hint: macOS 'brew install gh' | Linux https://cli.github.com/" >&2
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
gh_args=(run list --workflow "${WORKFLOW_FILE}" --limit "${LIMIT}")
if [[ -n "${BRANCH}" ]]; then
  gh_args+=(--branch "${BRANCH}")
  [[ "$QUIET" -eq 0 ]] && echo "(branch=${BRANCH} — passed to gh run list)"
fi
if ! rows="$(gh "${gh_args[@]}" \
  --json databaseId,headBranch,status,conclusion,event,displayTitle,createdAt,updatedAt \
  --jq '.[] | "\(.databaseId)\t\(.headBranch)\t\(.status)\t\(.conclusion // "n/a")\t\(.event)\t\(.displayTitle)"')"; then
  echo "CI_RUNS_CHECK FAIL: unable to fetch workflow runs via gh." >&2
  echo "Check workflow name, repo access, and auth state (gh auth status)." >&2
  exit 1
fi

output="$rows"
if [[ "$CANCELLED_ONLY" -eq 1 ]]; then
  [[ "$QUIET" -eq 0 ]] && echo "(filtered cancelled-only)"
  output="$(printf '%s\n' "$output" | awk -F '\t' '$4=="cancelled" {print}')"
fi
if [[ "$FAILED_ONLY" -eq 1 ]]; then
  [[ "$QUIET" -eq 0 ]] && echo "(filtered failed-only)"
  output="$(printf '%s\n' "$output" | awk -F '\t' '$3=="completed" && $4!="success" && $4!="cancelled" {print}')"
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
  # With --branch, gh returns runs for that ref only (newest first); first row is latest.
  latest_line="$(printf '%s\n' "$rows" | awk 'NF {print; exit}')"
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
if [[ "$FAIL_ON_FAILED" -eq 1 ]]; then
  failed_count="$(printf '%s\n' "$output" | awk -F '\t' '$3=="completed" && $4!="success" && $4!="cancelled" {n++} END {print n+0}')"
  if [[ "$failed_count" -gt 0 ]]; then
    echo "CI_RUNS_CHECK FAIL: found ${failed_count} failed run(s) in filtered output" >&2
    exit 1
  fi
  [[ "$QUIET" -eq 0 ]] && echo "CI_RUNS_CHECK PASS: no failed runs in filtered output"
fi

if [[ "$FAIL_ON_INCOMPLETE" -eq 1 ]]; then
  incomplete_count="$(printf '%s\n' "$output" | awk -F '\t' '$3!="completed" {n++} END {print n+0}')"
  if [[ "$incomplete_count" -gt 0 ]]; then
    echo "CI_RUNS_CHECK FAIL: found ${incomplete_count} incomplete run(s) in filtered output" >&2
    exit 1
  fi
  [[ "$QUIET" -eq 0 ]] && echo "CI_RUNS_CHECK PASS: no incomplete runs in filtered output"
fi

if [[ "$FAIL_ON_EMPTY" -eq 1 ]]; then
  row_count="$(printf '%s\n' "$output" | awk 'NF {n++} END {print n+0}')"
  if [[ "$row_count" -eq 0 ]]; then
    echo "CI_RUNS_CHECK FAIL: filtered output is empty" >&2
    exit 1
  fi
  [[ "$QUIET" -eq 0 ]] && echo "CI_RUNS_CHECK PASS: filtered output has ${row_count} row(s)"
fi

if [[ "$QUIET" -eq 0 && "$JSON_OUTPUT" -eq 0 ]]; then
  echo
  echo "Tip: under concurrency cancel-in-progress, older runs on the same branch may show cancelled."
  echo "Use the newest run on the branch/ref as source of truth."
fi

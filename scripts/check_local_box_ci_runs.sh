#!/usr/bin/env bash
# Quick helper: inspect recent local-box-baseline workflow runs.
set -euo pipefail

WORKFLOW_FILE="${WORKFLOW_FILE:-local-box-baseline.yml}"
LIMIT="${LIMIT:-10}"

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
gh run list --workflow "${WORKFLOW_FILE}" --limit "${LIMIT}" \
  --json databaseId,headBranch,status,conclusion,event,displayTitle,createdAt,updatedAt \
  --jq '.[] | "\(.databaseId)\t\(.headBranch)\t\(.status)\t\(.conclusion // "n/a")\t\(.event)\t\(.displayTitle)"'

echo
echo "Tip: under concurrency cancel-in-progress, older runs on the same branch may show cancelled."
echo "Use the newest run on the branch/ref as source of truth."

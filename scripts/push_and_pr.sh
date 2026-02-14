#!/usr/bin/env bash
# Push feature/ops-console-minimal and prepare PR evidence.
# Usage: REPO_URL=<your_https_or_ssh_url> ./scripts/push_and_pr.sh
# Example: REPO_URL=https://github.com/yourorg/project-anchor.git ./scripts/push_and_pr.sh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_URL="${REPO_URL:?Set REPO_URL (HTTPS or SSH)}"

cd "$ROOT"

echo "=== status ==="
git status -sb
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD

echo ""
echo "=== 1) add origin ==="
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

echo ""
echo "=== 2) verify remote ==="
git remote -v

echo ""
echo "=== 3) push ==="
git push -u origin feature/ops-console-minimal

echo ""
echo "=== 5) PR evidence (paste to PR description) ==="
tail -n 120 /tmp/anchor_e2e_merge_summary.out 2>/dev/null || echo "Run: tail -n 120 /tmp/anchor_e2e_merge_summary.out"

#!/usr/bin/env bash
# Run once after setting REPO_URL. Usage:
#   export REPO_URL=https://github.com/YOUR_ORG/project-anchor.git
#   ./scripts/do_push_and_pr.sh
set -e

REPO_URL="${REPO_URL:?Set REPO_URL, e.g. export REPO_URL=https://github.com/YOUR_ORG/project-anchor.git}"

echo "Adding origin..."
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

echo "Pushing..."
git push -u origin feature/ops-console-minimal

echo "Done. Open PR: base=main, compare=feature/ops-console-minimal"
echo "PR description: cat PR_DESCRIPTION.md"

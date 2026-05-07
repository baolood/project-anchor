#!/usr/bin/env bash
# Install repo-managed Git hooks (pre-commit: baseline + go-live rules).
# Run from anywhere: ./scripts/install_git_hooks.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "install_git_hooks FAIL: cannot resolve repository root" >&2
  exit 1
}

cd "$ROOT"

HOOKS_DIR="${ROOT}/.githooks"
if [[ ! -d "$HOOKS_DIR" ]]; then
  echo "install_git_hooks FAIL: missing ${HOOKS_DIR}" >&2
  exit 1
fi

git config core.hooksPath "${HOOKS_DIR}"
echo "install_git_hooks PASS: core.hooksPath=${HOOKS_DIR}"
echo "Remove with: git -C \"${ROOT}\" config --unset core.hooksPath"

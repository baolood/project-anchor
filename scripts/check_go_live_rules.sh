#!/usr/bin/env bash
set -euo pipefail

echo "[check] go-live rules"

FAIL=0

# Rule 1: CI reporter must remain stdout-only in PR guidance.
if ! grep -q "stdout-only" PR_DESCRIPTION.md; then
  echo "[fail] PR_DESCRIPTION.md missing stdout-only rule"
  FAIL=1
fi

# Rule 2: Local evidence must continue to use --out.
if ! grep -q -- "--out" PR_DESCRIPTION.md; then
  echo "[fail] PR_DESCRIPTION.md missing --out requirement"
  FAIL=1
fi

# Rule 3: Release notes must stay synced with the visible rule change.
if ! grep -q "stdout-only" RELEASE_NOTES.md; then
  echo "[fail] RELEASE_NOTES.md not synced"
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  echo "[result] FAIL"
  exit 1
fi

echo "[result] PASS"

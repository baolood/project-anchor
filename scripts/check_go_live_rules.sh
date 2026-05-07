#!/usr/bin/env bash
set -euo pipefail

echo "[check] go-live rules"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "[fail] cannot resolve repository root" >&2
  exit 1
}

RULES="${ROOT}/docs/RULES.md"
if [[ ! -f "$RULES" ]]; then
  echo "[fail] missing docs/RULES.md (SSOT)" >&2
  exit 1
fi

FAIL=0

# Rule 1: CI reporter remains stdout-only (see docs/RULES.md).
if ! grep -q "stdout-only" "$RULES"; then
  echo "[fail] docs/RULES.md missing stdout-only anchor" >&2
  FAIL=1
fi

# Rule 2: Local evidence continues to use --out (file path; see docs/RULES.md).
if ! grep -q -- "--out" "$RULES"; then
  echo "[fail] docs/RULES.md missing --out anchor" >&2
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  echo "[result] FAIL"
  exit 1
fi

echo "[result] PASS"

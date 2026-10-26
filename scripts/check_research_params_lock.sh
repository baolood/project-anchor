#!/usr/bin/env bash
# Verify every research/**/PARAMS.lock matches sha256 of its sibling PARAMS.md.
# Pre-registration audit only: no backtest, no network, no runtime.
# CI: local-box-baseline job "check".
set -euo pipefail

if (($# > 0)); then
  case "$1" in
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/check_research_params_lock.sh

For each research/**/PARAMS.lock, confirm the first field equals the sha256
of the sibling PARAMS.md (bytes on disk). A PARAMS.md without a lock fails.
Does not run strategy scripts and does not read market data.

EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Run: ./scripts/check_research_params_lock.sh --help" >&2
      exit 2
      ;;
  esac
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "[fail] cannot resolve repository root" >&2
  exit 1
}

python3 - "$ROOT" <<'PY'
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
research = root / "research"
if not research.is_dir():
    print("[fail] missing research/", file=sys.stderr)
    sys.exit(1)

locks = sorted(path for path in research.rglob("PARAMS.lock") if path.is_file())
params_files = sorted(path for path in research.rglob("PARAMS.md") if path.is_file())
if not locks:
    print("[fail] no PARAMS.lock under research/", file=sys.stderr)
    sys.exit(1)

fail = 0
locked_dirs = set()
for lock in locks:
    folder = lock.parent
    locked_dirs.add(folder)
    rel = folder.relative_to(root).as_posix()
    params = folder / "PARAMS.md"
    if not params.is_file():
        print(f"[fail] {rel}/PARAMS.md missing", file=sys.stderr)
        fail = 1
        continue
    digest = hashlib.sha256(params.read_bytes()).hexdigest()
    text = lock.read_text(encoding="utf-8")
    recorded = text.split()[0] if text.split() else ""
    if len(recorded) != 64 or any(ch not in "0123456789abcdef" for ch in recorded):
        print(f"[fail] {rel}/PARAMS.lock first field is not a sha256", file=sys.stderr)
        fail = 1
        continue
    if recorded != digest:
        print(
            f"[fail] {rel} PARAMS.lock {recorded} != sha256(PARAMS.md) {digest}",
            file=sys.stderr,
        )
        fail = 1
    else:
        print(f"[ok] {rel} {digest}")

for params in params_files:
    if params.parent not in locked_dirs:
        rel = params.parent.relative_to(root).as_posix()
        print(f"[fail] {rel}/PARAMS.md has no PARAMS.lock", file=sys.stderr)
        fail = 1

if fail:
    print("[fail] research PARAMS.lock check", file=sys.stderr)
    sys.exit(1)

print(f"[pass] research PARAMS.lock matches PARAMS.md ({len(locks)} families)")
PY

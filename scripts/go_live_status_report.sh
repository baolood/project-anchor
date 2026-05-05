#!/usr/bin/env bash
# Summarize go-live checklist status counts for daily standups.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKLIST_FILE="${CHECKLIST_FILE:-$ROOT/docs/GO_LIVE_CHECKLIST.md}"

if [[ ! -f "$CHECKLIST_FILE" ]]; then
  echo "GO_LIVE_STATUS FAIL: checklist file not found: $CHECKLIST_FILE" >&2
  exit 1
fi

python3 - "$CHECKLIST_FILE" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="ignore")

# Count explicit status markers used by the execution board.
statuses = ["TODO", "IN_PROGRESS", "BLOCKED", "DONE"]
counts = {s: len(re.findall(rf"`{s}`", text)) for s in statuses}

# Count checklist items as a rough denominator.
items = len(re.findall(r"^- \[ \] ", text, flags=re.MULTILINE))

print("GO_LIVE_STATUS_REPORT")
print(f"CHECKLIST_FILE={path}")
print(f"TOTAL_CHECK_ITEMS={items}")
for s in statuses:
    print(f"STATUS_{s}={counts[s]}")

# Basic health signal: blocked ratio among declared statuses.
declared = sum(counts.values())
blocked = counts["BLOCKED"]
ratio = 0.0 if declared == 0 else blocked / declared
print(f"BLOCKED_RATIO={ratio:.2%}")
PY

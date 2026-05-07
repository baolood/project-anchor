#!/usr/bin/env bash
# Summarize go-live checklist status counts for daily standups.
# CI: smoke step in local-box-baseline job "check"; see README.md (section "CI").
# Default CHECKLIST_FILE must match check_local_box_baseline.sh REQUIRED_PATHS unless you override CHECKLIST_FILE.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKLIST_FILE="${CHECKLIST_FILE:-$ROOT/docs/GO_LIVE_CHECKLIST.md}"
OUT_FILE="${OUT_FILE:-}"

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "GO_LIVE_STATUS FAIL: ${opt} requires a value." >&2
    exit 2
  fi
}

while (($# > 0)); do
  case "$1" in
    --out)
      require_value "--out" "${2:-}"
      OUT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/go_live_status_report.sh [--out <path>]

Options:
  --out <path>  Write report to file (stdout always prints; parent dirs created if missing).
                Must be a file path (directory targets, including trailing "/" paths, are rejected).

Env:
  CHECKLIST_FILE  Override checklist path.
  OUT_FILE        Optional output path (same as --out).

Standup evidence (tracked folder + gitignored *.out): see docs/GO_LIVE_CHECKLIST.md §7
and artifacts/go-live/README.md. Example:
  ./scripts/go_live_status_report.sh --out artifacts/go-live/go_live_daily_status_$(date +%F).out

CI: smoke step in local-box-baseline (job check). Job wall-clock caps: see .github/workflows/local-box-baseline.yml (timeout-minutes).
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

if [[ ! -f "$CHECKLIST_FILE" ]]; then
  echo "GO_LIVE_STATUS FAIL: checklist file not found: $CHECKLIST_FILE" >&2
  exit 1
fi

report="$(python3 - "$CHECKLIST_FILE" <<'PY'
import pathlib
import re
import sys
from datetime import datetime, timezone

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="ignore")

# Count explicit status markers used by the execution board.
statuses = ["TODO", "IN_PROGRESS", "BLOCKED", "DONE"]
counts = {s: len(re.findall(rf"`{s}`", text)) for s in statuses}

# Count checklist items as a rough denominator.
items = len(re.findall(r"^- \[ \] ", text, flags=re.MULTILINE))

print("GO_LIVE_STATUS_REPORT")
print(f"CHECKLIST_FILE={path}")
print(f"GENERATED_AT={datetime.now(timezone.utc).isoformat()}")
print(f"TOTAL_CHECK_ITEMS={items}")
for s in statuses:
    print(f"STATUS_{s}={counts[s]}")

# Basic health signal: blocked ratio among declared statuses.
declared = sum(counts.values())
blocked = counts["BLOCKED"]
ratio = 0.0 if declared == 0 else blocked / declared
print(f"BLOCKED_RATIO={ratio:.2%}")
PY
)"

echo "$report"

if [[ -n "${OUT_FILE}" ]]; then
  if [[ "${OUT_FILE}" == */ ]]; then
    echo "GO_LIVE_STATUS FAIL: --out expects a file path, got directory-like path: ${OUT_FILE}" >&2
    exit 2
  fi
  if [[ -d "${OUT_FILE}" ]]; then
    echo "GO_LIVE_STATUS FAIL: --out expects a file path, got directory: ${OUT_FILE}" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%s\n' "$report" > "$OUT_FILE"
  echo "WROTE_REPORT=$OUT_FILE"
fi

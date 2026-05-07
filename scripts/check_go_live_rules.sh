#!/usr/bin/env bash
# Enforces docs/RULES.md anchors + structural quality gates on docs/GO_LIVE_CHECKLIST.md:
#   - Rule 1: CI reporter is "stdout-only" (anchor in docs/RULES.md)
#   - Rule 2: local evidence uses "--out" (anchor in docs/RULES.md)
#   - Rule 3: WIP cap on §4 IN_PROGRESS items (default 14, override via GOLIVE_WIP_LIMIT)
#   - Rule 3b: optional WIP freeze from docs/RULES.md (baseline + until date; rejects cap inflation)
#   - Rule 4: §4 DONE items must carry machine-verifiable evidence (no "<link>" placeholders)
#   - Rule 5: §6 OPEN risks past their ETA must be RESOLVED or have ETA moved forward
# CI: invoked from .github/workflows/local-box-baseline.yml (job "check").
set -euo pipefail

echo "[check] go-live rules"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || {
  echo "[fail] cannot resolve repository root" >&2
  exit 1
}

RULES="${ROOT}/docs/RULES.md"
CHECKLIST="${ROOT}/docs/GO_LIVE_CHECKLIST.md"

if [[ ! -f "$RULES" ]]; then
  echo "[fail] missing docs/RULES.md (SSOT)" >&2
  exit 1
fi

if [[ ! -f "$CHECKLIST" ]]; then
  echo "[fail] missing docs/GO_LIVE_CHECKLIST.md" >&2
  exit 1
fi

WIP_LIMIT="${GOLIVE_WIP_LIMIT:-14}"

FAIL=0

if ! grep -q "stdout-only" "$RULES"; then
  echo "[fail] docs/RULES.md missing stdout-only anchor" >&2
  FAIL=1
fi

if ! grep -q -- "--out" "$RULES"; then
  echo "[fail] docs/RULES.md missing --out anchor" >&2
  FAIL=1
fi

for anchor in "WIP cap" "DONE evidence" "Risk ETA" "WIP freeze baseline" "WIP freeze until"; do
  if ! grep -q "$anchor" "$RULES"; then
    echo "[fail] docs/RULES.md missing '${anchor}' anchor" >&2
    FAIL=1
  fi
done

if ! python3 - "$RULES" "$CHECKLIST" "$WIP_LIMIT" <<'PY'
import re
import sys
from datetime import date
from pathlib import Path

rules_path = Path(sys.argv[1])
path = Path(sys.argv[2])
wip_limit = int(sys.argv[3])
rules_text = rules_path.read_text(encoding="utf-8")
text = path.read_text(encoding="utf-8")

today = date.today()
freeze_baseline_m = re.search(
    r"\*\*WIP freeze baseline:\*\*\s*\*\*(\d+)\*\*",
    rules_text,
)
freeze_until_m = re.search(
    r"\*\*WIP freeze until:\*\*\s*\*\*(\d{4}-\d{2}-\d{2})\*\*",
    rules_text,
)
freeze_baseline = int(freeze_baseline_m.group(1)) if freeze_baseline_m else None
freeze_until = (
    date.fromisoformat(freeze_until_m.group(1)) if freeze_until_m else None
)
freeze_active = (
    freeze_baseline is not None
    and freeze_until is not None
    and today <= freeze_until
)
if freeze_baseline_m is None or freeze_until_m is None:
    print(
        "[fail] docs/RULES.md: could not parse WIP freeze baseline / until "
        "(expected **WIP freeze baseline:** **N** and **WIP freeze until:** **YYYY-MM-DD**)",
        file=sys.stderr,
    )
    sys.exit(1)

sections = re.split(r"(?m)^(?=## \d+\))", text)
sec_by_num = {}
for sec in sections:
    m = re.match(r"## (\d+)\)", sec)
    if m:
        sec_by_num[int(m.group(1))] = sec

fail = False

sec4 = sec_by_num.get(4, "")
in_progress = len(re.findall(r"^\s*-\s*Status:\s*`IN_PROGRESS`", sec4, flags=re.MULTILINE))
done = len(re.findall(r"^\s*-\s*Status:\s*`DONE`", sec4, flags=re.MULTILINE))
todo = len(re.findall(r"^\s*-\s*Status:\s*`TODO`", sec4, flags=re.MULTILINE))
blocked = len(re.findall(r"^\s*-\s*Status:\s*`BLOCKED`", sec4, flags=re.MULTILINE))
effective_cap = wip_limit
if freeze_active:
    if wip_limit > freeze_baseline:
        print(
            f"[fail] WIP freeze active until {freeze_until}: GOLIVE_WIP_LIMIT={wip_limit} "
            f"exceeds freeze baseline {freeze_baseline}. Lower env, unset it, or end freeze in §9.",
            file=sys.stderr,
        )
        fail = True
    effective_cap = min(wip_limit, freeze_baseline)
    print(
        f"[info] WIP freeze ON (until {freeze_until}, baseline {freeze_baseline}); "
        f"effective cap {effective_cap}"
    )
else:
    print(
        f"[info] WIP freeze OFF (baseline {freeze_baseline}, until {freeze_until}, today {today})"
    )

print(f"[info] §4 status: TODO={todo} IN_PROGRESS={in_progress} BLOCKED={blocked} DONE={done} (WIP cap {wip_limit})")

if in_progress > effective_cap:
    print(
        f"[fail] WIP cap exceeded: §4 IN_PROGRESS={in_progress} > limit {effective_cap}. "
        f"Move an item to DONE or raise GOLIVE_WIP_LIMIT in a §9 review.",
        file=sys.stderr,
    )
    fail = True

items = re.split(r"(?m)^(?=- \[ \] )", sec4)
for it in items:
    if "Status:" not in it:
        continue
    if not re.search(r"Status:\s*`DONE`", it):
        continue
    title_m = re.search(r"- \[ \] \*\*(.+?)\*\*", it)
    title = title_m.group(1) if title_m else "<unknown>"
    ev_m = re.search(r"Evidence:\s*(.+)", it)
    if not ev_m:
        print(f"[fail] DONE item without Evidence line: {title}", file=sys.stderr)
        fail = True
        continue
    ev = ev_m.group(1).strip()
    if "<link>" in ev:
        print(f"[fail] DONE evidence still placeholder for: {title} -> {ev[:80]!r}", file=sys.stderr)
        fail = True
        continue
    if not re.search(r"(`[^`]+`|§\d+|commit\s+[0-9a-f]{6,})", ev):
        print(
            f"[fail] DONE evidence lacks verifiable anchor (need `path` / §N / commit <sha>): "
            f"{title} -> {ev[:80]!r}",
            file=sys.stderr,
        )
        fail = True

sec6 = sec_by_num.get(6, "")
risks = re.split(r"(?m)^(?=- Risk ID:)", sec6)
warn_window = 7
for r in risks:
    if "Risk ID:" not in r:
        continue
    rid_m = re.search(r"Risk ID:\s*\*\*(R-\d+)\*\*", r)
    rid = rid_m.group(1) if rid_m else "<unknown>"
    status_m = re.search(r"Status:\s*\*\*(\w+)\*\*", r)
    status_val = status_m.group(1) if status_m else "<unknown>"
    eta_m = re.search(r"ETA to close:\s*\*\*(\d{4}-\d{2}-\d{2})\*\*", r)
    if not eta_m:
        continue
    try:
        eta = date.fromisoformat(eta_m.group(1))
    except ValueError:
        continue
    days_left = (eta - today).days
    if status_val == "OPEN":
        if eta < today:
            print(
                f"[fail] {rid}: ETA {eta} passed (status OPEN). Resolve, or move ETA in §9 review.",
                file=sys.stderr,
            )
            fail = True
        elif days_left <= warn_window:
            print(f"[warn] {rid}: ETA {eta} in {days_left} day(s); status still OPEN")

if fail:
    sys.exit(1)
PY
then
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  echo "[result] FAIL"
  exit 1
fi

echo "[result] PASS"

#!/usr/bin/env bash
# Guardrail check: checklist scripts should run curl with timeout protection.
# CI: job checklist-curl-guardrails in local-box-baseline.yml; see README.md (section "CI").
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERBOSE=0
CHANGED_ONLY=0

while (($# > 0)); do
  case "$1" in
    --verbose)
      VERBOSE=1
      shift
      ;;
    --changed-only)
      CHANGED_ONLY=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/check_checklist_curl_guardrails.sh [--verbose] [--changed-only]

Options:
  --verbose       Print detailed scan information.
  --changed-only  Scan only changed checklist scripts (working tree, staged, untracked).

See also: README.md (section "CI") for workflow layout (this script runs in job checklist-curl-guardrails).
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

python3 - "$ROOT" "$VERBOSE" "$CHANGED_ONLY" <<'PY'
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
verbose = sys.argv[2] == "1"
changed_only = sys.argv[3] == "1"

all_scripts = sorted((root / "scripts").glob("checklist_*.sh"))
if changed_only:
    changed = set()

    def add_lines(cmd):
        proc = subprocess.run(
            cmd,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            if verbose:
                joined = " ".join(cmd)
                msg = proc.stderr.strip() or f"exit={proc.returncode}"
                print(f"[scan] skip source ({joined}): {msg}")
            return
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("scripts/checklist_") and line.endswith(".sh"):
                changed.add(line)

    add_lines(["git", "diff", "--name-only", "--diff-filter=AM", "HEAD", "--", "scripts/checklist_*.sh"])
    add_lines(["git", "diff", "--cached", "--name-only", "--diff-filter=AM", "--", "scripts/checklist_*.sh"])
    add_lines(["git", "ls-files", "--others", "--exclude-standard", "--", "scripts/checklist_*.sh"])

    scripts = [root / rel for rel in sorted(changed) if (root / rel).exists()]
else:
    scripts = all_scripts

if not scripts:
    if changed_only:
        print("CHECKLIST_CURL_GUARDRAILS PASS: no changed checklist scripts to scan")
    else:
        print("CHECKLIST_CURL_GUARDRAILS PASS: no checklist scripts found")
    sys.exit(0)

violations = []
checked_lines = 0
for path in scripts:
    if verbose:
        print(f"[scan] {path.relative_to(root).as_posix()}")
    for line_no, raw in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        checked_lines += 1
        # Ignore array appends / variable names that include 'curl' but are not invocations.
        if "curl_opts+=" in line or "curl_off_opts+=" in line:
            continue
        # Detect direct curl invocations in common forms:
        #   curl ...
        #   if ! curl ...
        #   var="$(curl ...)"
        if not re.search(r'(^|[=\(";\s])curl(\s|$)', line):
            continue
        if "--connect-timeout" in line and "--max-time" in line:
            continue
        if "CURL_FLAGS" in line:
            continue
        violations.append((path.relative_to(root).as_posix(), line_no, line))

if violations:
    print("CHECKLIST_CURL_GUARDRAILS FAIL: missing timeout guard on curl invocation(s)")
    for rel, line_no, line in violations:
        print(f"- {rel}:{line_no}: {line}")
    sys.exit(1)

scope = "changed checklist scripts" if changed_only else "checklist scripts"
print(f"CHECKLIST_CURL_GUARDRAILS PASS: {len(scripts)} {scope} scanned")
if verbose:
    print(f"[scan] non-comment/non-empty lines checked: {checked_lines}")
PY

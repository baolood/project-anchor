#!/usr/bin/env bash
# Guardrail check: checklist scripts should run curl with timeout protection.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$ROOT" <<'PY'
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
scripts = sorted((root / "scripts").glob("checklist_*.sh"))
if not scripts:
    print("CHECKLIST_CURL_GUARDRAILS PASS: no checklist scripts found")
    sys.exit(0)

violations = []
for path in scripts:
    for line_no, raw in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
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

print(f"CHECKLIST_CURL_GUARDRAILS PASS: {len(scripts)} checklist scripts scanned")
PY

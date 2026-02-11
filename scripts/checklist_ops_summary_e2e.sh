#!/usr/bin/env bash
# Ops summary e2e: GET /api/proxy/ops/summary returns counts + recent.
set -euo pipefail

OUT="${OUT:-/tmp/anchor_e2e_checklist_ops_summary_e2e_last.out}"
CONSOLE_URL="${CONSOLE_URL:-http://127.0.0.1:3000}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

PASS_OR_FAIL=FAIL
FAIL_REASON=""

parse_http() {
  python3 - "$1" <<'PY'
import sys
path = sys.argv[1]
raw = open(path, "rb").read().decode("utf-8", errors="replace")
raw = raw.replace("\r\n", "\n").replace("\r", "\n")
lines = raw.split("\n")
if not lines:
    print("0")
    print("")
    sys.exit(0)
parts = lines[0].strip().split()
status_code = parts[1] if len(parts) >= 2 else "0"
body_lines = []
found_blank = False
for i in range(1, len(lines)):
    if lines[i].strip() == "":
        found_blank = True
        continue
    if found_blank:
        body_lines.append(lines[i])
print(status_code)
print("\n".join(body_lines))
PY
}

echo "MODULE=ops_summary_e2e" > "$OUT"

echo "== Step0 Precheck =="
get_home="$tmpdir/get_home.txt"
curl -sS -i --noproxy '*' "$CONSOLE_URL/" -o "$get_home" || true
home_status="$(parse_http "$get_home" | head -1)"
if [ "$home_status" != "200" ]; then
  echo "HTTP_STATUS=0" >> "$OUT"
  echo "HAS_COUNTS=NO" >> "$OUT"
  echo "HAS_RECENT=NO" >> "$OUT"
  echo "PASS_OR_FAIL=FAIL" >> "$OUT"
  echo "FAIL_REASON=CONSOLE_NOT_READY" >> "$OUT"
  cat "$OUT"
  exit 1
fi

echo "== Step1 GET /api/proxy/ops/summary =="
summary_resp="$tmpdir/summary_resp.txt"
curl -sS -i --noproxy '*' "$CONSOLE_URL/api/proxy/ops/summary?minutes=30&limit=10" -o "$summary_resp" || true
summary_status="$(parse_http "$summary_resp" | head -1)"
summary_body="$tmpdir/summary_body.json"
parse_http "$summary_resp" | sed -n '2,$p' > "$summary_body"

echo "HTTP_STATUS=$summary_status" >> "$OUT"

if [ "$summary_status" != "200" ]; then
  echo "HAS_COUNTS=NO" >> "$OUT"
  echo "HAS_RECENT=NO" >> "$OUT"
  echo "PASS_OR_FAIL=FAIL" >> "$OUT"
  echo "FAIL_REASON=OPS_SUMMARY_HTTP_NOT_200" >> "$OUT"
  cat "$OUT"
  exit 1
fi

python3 - "$summary_body" <<'PY'
import json, sys
path = sys.argv[1]
try:
    d = json.load(open(path))
except Exception as e:
    print(f"JSON_PARSE_ERROR:{e}", file=sys.stderr)
    sys.exit(1)
counts = d.get("counts")
if not isinstance(counts, dict):
    print("MISSING_COUNTS", file=sys.stderr)
    sys.exit(2)
required = {"FAILED", "POLICY_BLOCK", "EXCEPTION", "KILL_SWITCH_ON"}
missing = required - set(counts.keys())
if missing:
    print(f"MISSING_KEYS:{missing}", file=sys.stderr)
    sys.exit(3)
recent = d.get("recent")
if not isinstance(recent, list):
    print("MISSING_RECENT", file=sys.stderr)
    sys.exit(4)
print("OK")
PY
json_ok=$?

if [ "$json_ok" -ne 0 ]; then
  echo "HAS_COUNTS=NO" >> "$OUT"
  echo "HAS_RECENT=NO" >> "$OUT"
  echo "PASS_OR_FAIL=FAIL" >> "$OUT"
  [ "$json_ok" -eq 2 ] && echo "FAIL_REASON=MISSING_COUNTS" >> "$OUT"
  [ "$json_ok" -eq 3 ] && echo "FAIL_REASON=MISSING_COUNTS_KEYS" >> "$OUT"
  [ "$json_ok" -eq 4 ] && echo "FAIL_REASON=MISSING_RECENT" >> "$OUT"
  [ "$json_ok" -eq 1 ] && echo "FAIL_REASON=JSON_PARSE_ERROR" >> "$OUT"
  cat "$OUT"
  exit 1
fi

echo "HAS_COUNTS=YES" >> "$OUT"
echo "HAS_RECENT=YES" >> "$OUT"
PASS_OR_FAIL=PASS
echo "PASS_OR_FAIL=$PASS_OR_FAIL" >> "$OUT"
echo "FAIL_REASON=" >> "$OUT"

cat "$OUT"
exit 0

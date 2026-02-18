#!/usr/bin/env bash
set -euo pipefail

MODULE=ops_audit_export_e2e
OUT=${OUT:-/tmp/anchor_e2e_checklist_ops_audit_export_e2e_last.out}
CONSOLE_URL=${CONSOLE_URL:-http://127.0.0.1:3000}

pass=YES
fail_reason=""

json_url="$CONSOLE_URL/api/proxy/ops/state/history/export?limit=5"
csv_url="$CONSOLE_URL/api/proxy/ops/state/history/export.csv?limit=5"

json_code=$(curl -s -o /tmp/anchor_tmp_ops_audit_export_json.out -w "%{http_code}" "$json_url" || true)
csv_code=$(curl -s -D /tmp/anchor_tmp_ops_audit_export_csv_headers.out -o /tmp/anchor_tmp_ops_audit_export_csv_body.out -w "%{http_code}" "$csv_url" || true)

has_header=NO
if grep -qi "ts,event_type,exec_mode,actor,source" /tmp/anchor_tmp_ops_audit_export_csv_body.out 2>/dev/null; then
  has_header=YES
fi

if [[ "$json_code" != "200" ]]; then pass=NO; fail_reason="JSON_HTTP_$json_code"; fi
if [[ "$csv_code" != "200" ]]; then pass=NO; fail_reason="${fail_reason:+$fail_reason,}CSV_HTTP_$csv_code"; fi
if [[ "$has_header" != "YES" ]]; then pass=NO; fail_reason="${fail_reason:+$fail_reason,}CSV_HEADER_MISSING"; fi

cat > "$OUT" <<EOF2
MODULE=$MODULE
JSON_HTTP_STATUS=$json_code
CSV_HTTP_STATUS=$csv_code
CSV_HAS_HEADER=$has_header
PASS_OR_FAIL=$( [[ "$pass" == "YES" ]] && echo PASS || echo FAIL )
FAIL_REASON=$fail_reason
EOF2

echo "OUT=$OUT"
cat "$OUT"

if [[ "$pass" != "YES" ]]; then exit 1; fi

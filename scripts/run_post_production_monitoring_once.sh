#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${POST_PRODUCTION_MONITORING_OUTPUT_DIR:-/var/lib/project-anchor/reports}"
RUN_JSON="$OUTPUT_DIR/post_production_monitoring_run.json"

cd "$ROOT"

mkdir -p "$OUTPUT_DIR"
POST_PRODUCTION_MONITORING_OUTPUT_DIR="$OUTPUT_DIR" python3 scripts/run_post_production_monitoring.py

python3 - "$RUN_JSON" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
boundary = data.get("boundary") if isinstance(data.get("boundary"), dict) else {}
checks = {
    "result": data.get("result") == "PASS",
    "credential_file_read": boundary.get("credential_file_read") == "NO",
    "secret_value_disclosed": boundary.get("secret_value_disclosed") == "NO",
    "production_signing_executed": boundary.get("production_signing_executed") == "NO",
    "production_http_network_attempted": boundary.get("production_http_network_attempted") == "NO",
    "new_production_request_sent": boundary.get("new_production_request_sent") == "NO",
    "second_production_request_sent": boundary.get("second_production_request_sent") == "NO",
    "canary_rerun": boundary.get("canary_rerun") == "NO",
    "runtime_modified": boundary.get("runtime_modified") == "NO",
    "go_live": boundary.get("go_live") == "NO-GO",
    "live_trading": boundary.get("live_trading") == "NO-GO",
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    print("POST_PRODUCTION_MONITORING_ONCE_RESULT=BLOCKED")
    print("FAILED_CHECKS=" + ",".join(failed))
    sys.exit(1)
print("POST_PRODUCTION_MONITORING_ONCE_RESULT=PASS")
print("RUN_STATUS=" + str(data.get("status")))
print("CREDENTIAL_FILE_READ=" + str(boundary.get("credential_file_read")))
print("NEW_PRODUCTION_REQUEST_SENT=" + str(boundary.get("new_production_request_sent")))
print("SECOND_PRODUCTION_REQUEST_SENT=" + str(boundary.get("second_production_request_sent")))
print("GO_LIVE=" + str(boundary.get("go_live")))
print("LIVE_TRADING=" + str(boundary.get("live_trading")))
PY

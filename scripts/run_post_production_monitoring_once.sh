#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${POST_PRODUCTION_MONITORING_OUTPUT_DIR:-/var/lib/project-anchor/reports}"
RUN_JSON="$OUTPUT_DIR/post_production_monitoring_run.json"
TELEGRAM_PAYLOAD_JSON="$OUTPUT_DIR/post_production_monitoring_telegram_payload.json"
TELEGRAM_PAYLOAD_MD="$OUTPUT_DIR/post_production_monitoring_telegram_payload.md"
TELEGRAM_SEND_JSON="$OUTPUT_DIR/post_production_monitoring_telegram_send_result.json"
TELEGRAM_SEND_MD="$OUTPUT_DIR/post_production_monitoring_telegram_send_result.md"
TELEGRAM_AUTO_SEND="${POST_PRODUCTION_MONITORING_TELEGRAM_AUTO_SEND:-0}"

cd "$ROOT"

mkdir -p "$OUTPUT_DIR"
POST_PRODUCTION_MONITORING_OUTPUT_DIR="$OUTPUT_DIR" python3 scripts/run_post_production_monitoring.py
python3 scripts/render_post_production_monitoring_telegram_payload.py \
  --notification-json "$OUTPUT_DIR/post_production_monitoring_alert_notification.json" \
  --json-out "$TELEGRAM_PAYLOAD_JSON" \
  --markdown-out "$TELEGRAM_PAYLOAD_MD"
TELEGRAM_SEND_ARGS=(
  --payload-json "$TELEGRAM_PAYLOAD_JSON"
  --json-out "$TELEGRAM_SEND_JSON"
  --markdown-out "$TELEGRAM_SEND_MD"
)
if [[ "$TELEGRAM_AUTO_SEND" == "1" ]]; then
  TELEGRAM_SEND_ARGS+=(--execute)
fi
set +e
python3 scripts/send_post_production_monitoring_telegram_alert.py "${TELEGRAM_SEND_ARGS[@]}"
TELEGRAM_SEND_EXIT=$?
set -e

python3 - "$RUN_JSON" "$TELEGRAM_SEND_JSON" "$TELEGRAM_SEND_EXIT" "$TELEGRAM_AUTO_SEND" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
telegram_send_path = Path(sys.argv[2])
telegram_send_exit = int(sys.argv[3])
telegram_auto_send = sys.argv[4]
data = json.loads(path.read_text(encoding="utf-8"))
telegram_send = json.loads(telegram_send_path.read_text(encoding="utf-8"))
boundary = data.get("boundary") if isinstance(data.get("boundary"), dict) else {}
telegram_boundary = (
    telegram_send.get("boundary") if isinstance(telegram_send.get("boundary"), dict) else {}
)
telegram_status = telegram_send.get("status")
telegram_ok = (
    telegram_send_exit == 0
    and telegram_send.get("result") == "PASS"
    and telegram_send.get("send_result") == "DELIVERED"
) or (
    telegram_send_exit == 1
    and telegram_send.get("result") == "BLOCKED"
    and telegram_status
    in {
        "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_BLOCKED",
        "POST_PRODUCTION_MONITORING_TELEGRAM_SEND_SUPPRESSED",
    }
    and telegram_send.get("send_attempted") == "NO"
)
checks = {
    "result": data.get("result") == "PASS",
    "telegram_sender_fail_closed_or_delivered": telegram_ok,
    "telegram_secret_not_disclosed": telegram_boundary.get("secret_value_disclosed") == "NO",
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
print("TELEGRAM_AUTO_SEND=" + str(telegram_auto_send))
print("TELEGRAM_SEND_STATUS=" + str(telegram_send.get("status")))
print("TELEGRAM_SEND_RESULT=" + str(telegram_send.get("result")))
print("TELEGRAM_SEND_ATTEMPTED=" + str(telegram_send.get("send_attempted")))
print("TELEGRAM_HTTP_ATTEMPTED=" + str(telegram_boundary.get("telegram_http_attempted")))
print("CREDENTIAL_FILE_READ=" + str(boundary.get("credential_file_read")))
print("NEW_PRODUCTION_REQUEST_SENT=" + str(boundary.get("new_production_request_sent")))
print("SECOND_PRODUCTION_REQUEST_SENT=" + str(boundary.get("second_production_request_sent")))
print("GO_LIVE=" + str(boundary.get("go_live")))
print("LIVE_TRADING=" + str(boundary.get("live_trading")))
PY

#!/usr/bin/env bash
set -euo pipefail

UNIT_DIR="${POST_PRODUCTION_MONITORING_UNIT_DIR:-/etc/systemd/system}"
SERVICE_NAME="project-anchor-post-production-monitoring.service"
TIMER_NAME="project-anchor-post-production-monitoring.timer"

if [[ "$(id -u)" != "0" ]]; then
  echo "POST_PRODUCTION_MONITORING_TIMER_UNINSTALL_RESULT=BLOCKED"
  echo "FAIL_REASON=must_run_as_root"
  exit 1
fi

systemctl disable --now "$TIMER_NAME" >/dev/null 2>&1 || true
rm -f "$UNIT_DIR/$SERVICE_NAME" "$UNIT_DIR/$TIMER_NAME"
systemctl daemon-reload

echo "POST_PRODUCTION_MONITORING_TIMER_UNINSTALL_RESULT=PASS"
echo "SERVICE_REMOVED=$SERVICE_NAME"
echo "TIMER_REMOVED=$TIMER_NAME"
echo "CREDENTIAL_FILE_READ=NO"
echo "NEW_PRODUCTION_REQUEST_SENT=NO"
echo "SECOND_PRODUCTION_REQUEST_SENT=NO"
echo "GO_LIVE=NO-GO"
echo "LIVE_TRADING=NO-GO"

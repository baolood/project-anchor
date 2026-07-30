#!/usr/bin/env bash
set -euo pipefail

ROOT="${PROJECT_ANCHOR_ROOT:-/root/project-anchor}"
OUTPUT_DIR="${POST_PRODUCTION_MONITORING_OUTPUT_DIR:-/var/lib/project-anchor/reports}"
INTERVAL_MINUTES="${POST_PRODUCTION_MONITORING_INTERVAL_MINUTES:-15}"
UNIT_DIR="${POST_PRODUCTION_MONITORING_UNIT_DIR:-/etc/systemd/system}"
REPORT_DIR="${POST_PRODUCTION_MONITORING_REPORT_DIR:-$OUTPUT_DIR}"
SERVICE_NAME="project-anchor-post-production-monitoring.service"
TIMER_NAME="project-anchor-post-production-monitoring.timer"

if [[ "$(id -u)" != "0" ]]; then
  echo "POST_PRODUCTION_MONITORING_TIMER_INSTALL_RESULT=BLOCKED"
  echo "FAIL_REASON=must_run_as_root"
  exit 1
fi

if [[ ! -x "$ROOT/scripts/run_post_production_monitoring_once.sh" ]]; then
  echo "POST_PRODUCTION_MONITORING_TIMER_INSTALL_RESULT=BLOCKED"
  echo "FAIL_REASON=monitoring_once_script_missing_or_not_executable"
  exit 1
fi

install -d -m 755 "$OUTPUT_DIR"

python3 "$ROOT/scripts/build_post_production_monitoring_timer_units.py" \
  --project-root "$ROOT" \
  --output-dir "$OUTPUT_DIR" \
  --interval-minutes "$INTERVAL_MINUTES" \
  --unit-dir "$UNIT_DIR" \
  --report-dir "$REPORT_DIR"

systemctl daemon-reload
systemctl enable --now "$TIMER_NAME"
systemctl list-timers --all "$TIMER_NAME" --no-pager

echo "POST_PRODUCTION_MONITORING_TIMER_INSTALL_RESULT=PASS"
echo "SERVICE=$SERVICE_NAME"
echo "TIMER=$TIMER_NAME"
echo "OUTPUT_DIR=$OUTPUT_DIR"
echo "INTERVAL_MINUTES=$INTERVAL_MINUTES"
echo "CREDENTIAL_FILE_READ=NO"
echo "NEW_PRODUCTION_REQUEST_SENT=NO"
echo "SECOND_PRODUCTION_REQUEST_SENT=NO"
echo "GO_LIVE=NO-GO"
echo "LIVE_TRADING=NO-GO"

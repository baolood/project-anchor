#!/usr/bin/env bash
# Install the read-only host fault alarm units. Run on the host, as root.
# Does not restart Anchor services, does not read the webhook file, and does
# not change sealed ledger StateDirectory permissions.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
UNIT_DIR="${ANCHOR_FAULT_UNIT_DIR:-/etc/systemd/system}"

if [[ "$(id -u)" != "0" ]]; then
  echo "FAULT_ALARM_INSTALL=BLOCKED"
  echo "FAIL_REASON=must_run_as_root"
  exit 1
fi

case "$UNIT_DIR" in
  /var/lib/private*|/var/lib/anchor-official-ledger*|/var/lib/anchor-ledger-mirror*)
    echo "FAULT_ALARM_INSTALL=BLOCKED"
    echo "FAIL_REASON=unit_dir_rejected"
    exit 1
    ;;
esac

if [[ "$REPO_ROOT" == *"#"* || "$REPO_ROOT" == *"|"* ]]; then
  echo "FAULT_ALARM_INSTALL=BLOCKED"
  echo "FAIL_REASON=repo_root_rejected"
  exit 1
fi

if [[ ! -f "$SCRIPT_DIR/probe.py" ]]; then
  echo "FAULT_ALARM_INSTALL=BLOCKED"
  echo "FAIL_REASON=probe_missing"
  exit 1
fi

install -d -m 0755 "$UNIT_DIR"
tmp=$(mktemp)
sed "s#/root/project-anchor#${REPO_ROOT}#g" "$SCRIPT_DIR/anchor-fault-alarm.service" > "$tmp"
install -m 0644 "$tmp" "$UNIT_DIR/anchor-fault-alarm.service"
rm -f "$tmp"
install -m 0644 "$SCRIPT_DIR/anchor-fault-alarm.timer" "$UNIT_DIR/anchor-fault-alarm.timer"
systemctl daemon-reload

# Default: enable the timer for the next boot and do not start it. Starting
# posts to the webhook. ANCHOR_FAULT_START_NOW=1 starts only after a dry-run
# whose fault_count is 0.
if [[ "${ANCHOR_FAULT_START_NOW:-0}" == "1" ]]; then
  dry_dir=$(mktemp -d)
  dry_out=$(
    PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/anchor-backend" \
      python3 "$SCRIPT_DIR/probe.py" --dry-run --repo-root "$REPO_ROOT" --state-dir "$dry_dir"
  ) || {
    rm -rf "$dry_dir"
    echo "FAULT_ALARM_INSTALL=PASS"
    echo "FAULT_ALARM_START=BLOCKED"
    echo "FAIL_REASON=dry_run_failed"
    echo "TIMER_STARTED=NO"
    exit 1
  }
  rm -rf "$dry_dir"
  fault_count=$(printf '%s' "$dry_out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["fault_count"])')
  if [[ "$fault_count" != "0" ]]; then
    echo "FAULT_ALARM_INSTALL=PASS"
    echo "FAULT_ALARM_START=BLOCKED"
    echo "FAIL_REASON=dry_run_faults"
    echo "FAULT_COUNT=$fault_count"
    echo "TIMER_STARTED=NO"
    exit 1
  fi
  systemctl enable --now anchor-fault-alarm.timer
  systemctl start anchor-fault-alarm.service
  echo "TIMER_STARTED=YES"
else
  systemctl enable anchor-fault-alarm.timer
  echo "TIMER_STARTED=NO"
fi

echo "FAULT_ALARM_INSTALL=PASS"
echo "SERVICE=anchor-fault-alarm.service"
echo "TIMER=anchor-fault-alarm.timer"
echo "REPO_ROOT=$REPO_ROOT"
echo "LEDGER_STATEDIRECTORY_UNCHANGED=YES"
echo "WEBHOOK_ENV_PRINTED=NO"
echo "READ_ONLY=YES"

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
systemctl enable --now anchor-fault-alarm.timer
systemctl start anchor-fault-alarm.service

echo "FAULT_ALARM_INSTALL=PASS"
echo "SERVICE=anchor-fault-alarm.service"
echo "TIMER=anchor-fault-alarm.timer"
echo "REPO_ROOT=$REPO_ROOT"
echo "LEDGER_STATEDIRECTORY_UNCHANGED=YES"
echo "WEBHOOK_ENV_PRINTED=NO"
echo "READ_ONLY=YES"

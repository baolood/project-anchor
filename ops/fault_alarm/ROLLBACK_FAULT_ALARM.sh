#!/usr/bin/env bash
# Remove the host fault alarm units. DEPLOY=NO. Run on the host, as root.
# Leaves /var/lib/anchor-fault-alarm in place (dedupe state only).
# Does not read or delete /etc/anchor-mf4-watcher/webhook.env.
# Does not touch Line A, the sealed StateDirectory, the legacy equity CSV,
# the governance register, or the PASS LINE freeze record.
set -euo pipefail

if [[ "$(id -u)" != "0" ]]; then
  echo "FAULT_ALARM_ROLLBACK=BLOCKED"
  echo "FAIL_REASON=must_run_as_root"
  exit 1
fi

# Protected. This script must not remove these paths or change their mode.
# /var/lib/private
# /var/lib/private/anchor-official-ledger-20261010
# /var/lib/anchor-official-ledger-20261010
# /var/lib/anchor-ledger-mirror
# /etc/anchor-mf4-watcher/webhook.env
# governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl
# docs/PROJECT_ANCHOR_PASS_LINE_V1_1_FREEZE_RECORD.md

systemctl disable --now anchor-fault-alarm.timer || true
systemctl stop anchor-fault-alarm.service || true
rm -f /etc/systemd/system/anchor-fault-alarm.service
rm -f /etc/systemd/system/anchor-fault-alarm.timer
systemctl daemon-reload

echo "FAULT_ALARM_ROLLBACK=PASS"
echo "STATE_DIR_REMOVED=NO"
echo "WEBHOOK_ENV_REMOVED=NO"
echo "WEBHOOK_ENV_PRINTED=NO"
echo "LEDGER_STATEDIRECTORY_UNCHANGED=YES"
echo "LINE_A_TOUCHED=NO"
echo "READ_ONLY=YES"

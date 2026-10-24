#!/usr/bin/env bash
# Undo the MF4 host watcher unit. DEPLOY=NO. This file is a template.
# It stops anchor-mf4-watcher.service and removes that unit file.
# It does not delete /var/lib/anchor-mf4-watcher, and it does not read,
# print, or delete /etc/anchor-mf4-watcher/webhook.env.
# It does not touch Line A, the sealed StateDirectory, the legacy equity
# CSV, the governance register, or the PASS LINE freeze record.
set -euo pipefail

if [[ "$(id -u)" != "0" ]]; then
  echo "MF4_WATCHER_ROLLBACK=BLOCKED" >&2
  echo "FAIL_REASON=must_run_as_root" >&2
  exit 1
fi

# Protected. This script must not remove these paths.
# /var/lib/private
# /var/lib/private/anchor-official-ledger-20261010
# /var/lib/anchor-official-ledger-20261010
# /var/lib/anchor-ledger-mirror
# /etc/anchor-mf4-watcher/webhook.env
# governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl
# docs/PROJECT_ANCHOR_PASS_LINE_V1_1_FREEZE_RECORD.md

systemctl disable --now anchor-mf4-watcher.service || true
rm -f /etc/systemd/system/anchor-mf4-watcher.service
systemctl daemon-reload

echo "MF4_WATCHER_ROLLBACK=PASS"
echo "WATCHER_DATA_REMOVED=NO"
echo "WEBHOOK_ENV_REMOVED=NO"
echo "WEBHOOK_ENV_PRINTED=NO"
echo "LINE_A_TOUCHED=NO"
echo "DEPLOY=NO"
echo "LIVE_TRADING=NO-GO"

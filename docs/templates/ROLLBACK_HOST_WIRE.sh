#!/usr/bin/env bash
# Undo the C6 host wire. DEPLOY=NO. This file is a template.
# It stops the C6 timer and service, removes those unit files, and removes
# the MCP drop-in. It does not delete series data and it does not touch
# Line A, the sealed StateDirectory, the legacy equity CSV, the governance
# register, or the PASS LINE freeze record.
set -euo pipefail

if [[ "$(id -u)" != "0" ]]; then
  echo "C6_HOST_WIRE_ROLLBACK=BLOCKED" >&2
  echo "FAIL_REASON=must_run_as_root" >&2
  exit 1
fi

# Protected. This script must not remove these paths.
# /var/lib/private
# /var/lib/private/anchor-official-ledger-20261010
# /var/lib/anchor-official-ledger-20261010
# /var/lib/anchor-ledger-mirror
# /etc/systemd/system/anchor-official-ledger.service
# /etc/systemd/system/anchor-official-ledger.timer
# /etc/systemd/system/anchor-ledger-readonly-mirror.service
# /etc/systemd/system/anchor-ledger-readonly-mirror.timer
# governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl

systemctl disable --now anchor-official-ledger-c6.timer
systemctl disable --now anchor-official-ledger-c6.service || true
rm -f /etc/systemd/system/anchor-official-ledger-c6.service
rm -f /etc/systemd/system/anchor-official-ledger-c6.timer
rm -f /etc/systemd/system/anchor-control-mcp.service.d/30-c6-series.conf
rmdir /etc/systemd/system/anchor-control-mcp.service.d 2>/dev/null || true
systemctl daemon-reload
systemctl restart anchor-control-mcp.service

echo "C6_HOST_WIRE_ROLLBACK=PASS"
echo "SERIES_DATA_REMOVED=NO"
echo "LINE_A_TOUCHED=NO"
echo "DEPLOY=NO"
echo "LIVE_TRADING=NO-GO"

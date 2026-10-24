# ANCHOR HOST FAULT ALARM V1

DEPLOY=NO. Nothing in this change installs a unit or posts a webhook. The host checkout stays `/root/project-anchor` when an operator later runs the install script.

The 15-minute `project-anchor-post-production-monitoring.timer` re-checks the stored 2026-08-06 Binance order governance files. It does not check whether `anchor-mf4-watcher` or the official ledger are alive, and its Telegram sender stays off unless `POSTPRODUCTION_MONITORING_TELEGRAM_AUTO_SEND=1`. This probe is the host-side alarm for those gaps. The old timer is left in place.

## What is checked

Every 5 minutes the oneshot `anchor-fault-alarm.service` runs `ops/fault_alarm/probe.py`. The only process call is `systemctl show` on names taken from `anchor-backend/app/mcp/inventory.py`, plus three units that inventory classifies but does not put on the default allowlist.

| Check | Fault when |
| --- | --- |
| Long-running services | `ActiveState` is not `active`, or the unit is not loaded. The list is `RECOMMENDED_SERVICE_UNITS` plus `anchor-mf4-watcher.service` and `anchor-control-mcp.service`. |
| Ledger oneshots | `anchor-official-ledger.service`, `anchor-official-ledger-c6.service`, and `anchor-ledger-readonly-mirror.service` are not loaded, or the last run is not `Result=success` while idle. An in-progress run is healthy. |
| Timers | `RECOMMENDED_TIMER_UNITS` plus `anchor-official-ledger-c6.timer`. Not loaded, not active, `Result=failed`, never fired while nothing is scheduled, next elapse more than 10 minutes overdue, or no next elapse and the last fire is more than 2 hours old. A future elapse means the timer is armed. A loaded companion service that is not intentionally disabled is held to the same oneshot or long-running rule. |
| Backend | `GET http://127.0.0.1:8000/health` is not ok. The URL is the allowlisted probe in `app.mcp.backend_probe`. The body is not copied into the alert. |
| MF4 decision | More than 20 minutes after the latest completed 4h BTC close, `mf4_forward_events.jsonl` has no `SIGNAL_4H` or `SIGNAL_4H_SKIPPED` for that close. |
| Kill switch | State is `OPEN`, or the switch is unreadable. `CLOSED` with `enabled` false is healthy. The reader is `app.mcp.status.read_kill_switch`. |
| Go-live | The post-production guard is not blocked. |
| Live trading | The post-production guard is not blocked. |

`INTENTIONALLY_DISABLED` units are not faults. `anchor-fault-alarm.service` and `anchor-fault-alarm.timer` are `AUXILIARY` in the inventory and are not on the PASS allowlist. This alarm does not change what gates MCP PASS.

### MF4 decision

The watcher writes one row per completed 4h bar to `/var/lib/anchor-mf4-watcher/mf4_forward_events.jsonl` (`MF4_OUT_DIR`). A decision is `event_type` `SIGNAL_4H` or `SIGNAL_4H_SKIPPED` whose `bar4h_close_utc` or `signal_available_at` equals the close. Closes are UTC instants on a 14400-second grid (`00:00`, `04:00`, `08:00`, `12:00`, `16:00`, `20:00`). The probe reads the tail of that file and does not follow symlinks. The 20 minutes after a close are grace, so a bar that just closed does not page. A missing or sealed path after grace is a fault. The sealed ledger is not opened.

### Go-live and live trading

These are the two halves of `go_live_and_live_trading_blocked` in `scripts/generate_post_production_monitoring_snapshot.py`.

- `reports/production_execution_readiness.json` blockers include `go-live not authorized` and `live trading not authorized`.
- `reports/post_production_operations_decision.json` boundary `go_live` and `live_trading` are `NO-GO`.

Each flag is its own fault. If either file is unreadable, both faults fire. The probe does not refresh those reports and does not send an order.

### Kill switch

`ANCHOR_KILL_SWITCH=1` in the environment is `OPEN`. Otherwise the probe reads `REDIS_URL` from `/etc/project-anchor/anchor-control-mcp.env` when it is not already set, then uses the MCP reader. A missing Redis client, a missing URL, or a failed read is unreadable, which pages. The MCP token in that file is discarded and is not logged. An unread switch is not treated as closed.

## What the receiver sees

Market signals from the MF4 watcher use `signal`, `strategy`, and `source=anchor-host`. Fault posts use `type=anchor_fault` and `source=anchor-fault-alarm`. The HTTP `User-Agent` is `anchor-fault-alarm/1.0`. `MF4_WEBHOOK_ENABLED` does not gate this probe. The URL and key still come from the watcher credential:

- systemd `LoadCredential=webhook:/etc/anchor-mf4-watcher/webhook.env` (`$CREDENTIALS_DIRECTORY/webhook`), or
- `MF4_WEBHOOK_ENV_FILE`, or
- `/etc/anchor-mf4-watcher/webhook.env` when neither of those is set

Keys are `EVAL_WEBHOOK_URL`, `EVAL_WEBHOOK_KEY`, `EVAL_WEBHOOK_KEY_HEADER` (default `Authorization`), and `EVAL_WEBHOOK_KEY_FORMAT` (default `Bearer {key}`). One POST, 10 second timeout. The next timer run retries a failed post. The URL, the key, and the header value are not written to the payload, the state file, or the journal line.

`LoadCredential=` requires the webhook file to exist, the same way the MF4 watcher unit does. If the file is absent, systemd does not start the oneshot. A manual `probe.py` run still starts, prints the faults under `--dry-run`, and skips the post with `delivery skipped credentials_missing`.

A new fault:

```json
{
  "check": "service:anchor-mf4-watcher.service",
  "detail": "anchor-mf4-watcher.service is not active (inactive/dead); result=success",
  "event_id": "fault-0123456789abcdef0123",
  "repeat": false,
  "severity": "critical",
  "since": "2026-10-24T12:05:00Z",
  "source": "anchor-fault-alarm",
  "state": "fault",
  "time_utc": "2026-10-24T12:10:00Z",
  "type": "anchor_fault"
}
```

`check` is the unit or guard name. `since` is when the probe first saw this detail (or the unit's inactive timestamp when systemd provides one). `severity` is `critical` for a fault and `info` for a recovery. `detail` is one short sentence. `repeat` is false on the first post and on a detail change, and true on the 12 hour reminder.

When the fault clears, one recovery post uses the same `type` and `check`, with `state` `recovered` and `severity` `info`:

```json
{
  "check": "service:anchor-mf4-watcher.service",
  "detail": "service:anchor-mf4-watcher.service cleared",
  "repeat": false,
  "severity": "info",
  "since": "2026-10-24T12:05:00Z",
  "source": "anchor-fault-alarm",
  "state": "recovered",
  "type": "anchor_fault"
}
```

Dedupe state is `/var/lib/anchor-fault-alarm/fault_alarm_state.json` (`StateDirectory=anchor-fault-alarm`). The same fingerprint is silent until 12 hours after `last_alert`. A changed detail posts again. A failed POST does not move `last_alert`, so the next run tries again. Recovery is sent once.

Check names:

| `check` | Meaning |
| --- | --- |
| `service:<unit>` | Long-running unit down, or oneshot last result not success |
| `timer:<unit>` | Timer not loaded, not active, failed, or not firing |
| `mf4:decision` | No 4h decision after the grace, or the log is unreadable |
| `kill_switch` | Open or unreadable |
| `guard:go_live` | Go-live is not blocked, or the evidence is unreadable |
| `guard:live_trading` | Live trading is not blocked, or the evidence is unreadable |
| `backend:127.0.0.1:8000` | Loopback health is not ok |
| `systemd:show` | `systemctl` is missing |

## Dry-run

Prints the JSON that would be posted and does not write state or open a socket to the webhook.

```bash
cd /path/to/project-anchor
PYTHONPATH=.:anchor-backend python3 ops/fault_alarm/probe.py --dry-run --state-dir /tmp/anchor-fault-alarm-state
```

On a machine that is not the Vultr host, missing units show up as faults in that JSON. That is the same detection the timer uses. `--dry-run` still reads local unit state and loopback health when those calls are available.

## Install

Run on the host, from the checkout, as root. This repository change does not run it.

```bash
cd /root/project-anchor
sudo ./ops/fault_alarm/install_fault_alarm.sh
```

The script copies the unit files into `/etc/systemd/system`, rewrites the `/root/project-anchor` prefix when the checkout path differs, reloads systemd, enables the timer, and starts one probe. It does not print the webhook file. It refuses a unit directory under the sealed ledger paths.

Confirm:

```bash
systemctl status anchor-fault-alarm.timer --no-pager
systemctl list-timers anchor-fault-alarm.timer --no-pager
```

Journal lines look like `FAULT_ALARM faults=0 sent=0 recovered=0`. A delivery problem is `delivery skipped credentials_missing` or `delivery failed network_error`. Those lines do not include the URL or the key.

## Rollback

```bash
cd /root/project-anchor
sudo ./ops/fault_alarm/ROLLBACK_FAULT_ALARM.sh
```

This disables the timer, stops the oneshot if it is running, and deletes the two unit files. It leaves `/var/lib/anchor-fault-alarm` in place. It does not read or delete the webhook env file. It does not chmod or remove:

- `/var/lib/private`
- `/var/lib/private/anchor-official-ledger-20261010`
- `/var/lib/anchor-official-ledger-20261010`
- `/var/lib/anchor-ledger-mirror`
- the legacy equity CSV
- `governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl`
- `docs/PROJECT_ANCHOR_PASS_LINE_V1_1_FREEZE_RECORD.md`

The service sandbox also lists those ledger paths as `InaccessiblePaths`, so the probe process cannot write them.

## Verify

```bash
cd /path/to/project-anchor
PYTHONPATH=.:anchor-backend python3 -m unittest tests.test_host_fault_alarm
```

## Out of scope

No restarts, no database writes, no orders, no exchange calls, no edits to Line A, the legacy equity CSV, the governance register, or the PASS LINE freeze record. The post-production monitoring timer is unchanged.

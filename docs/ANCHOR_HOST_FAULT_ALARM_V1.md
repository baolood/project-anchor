# ANCHOR HOST FAULT ALARM V1

DEPLOY=NO. Nothing in this change installs a unit or posts a webhook. The host checkout stays `/root/project-anchor` when an operator later runs the install script.

The 15-minute `project-anchor-post-production-monitoring.timer` re-checked the stored 2026-08-06 Binance order governance files. It did not check whether `anchor-mf4-watcher` or the official ledger were alive. At 20:02 Asia/Shanghai on 2026-10-24 that timer and `project-anchor-post-production-monitoring.service` were stopped and disabled. Both names are in `RETIRED_UNITS` in `anchor-backend/app/mcp/inventory.py`. This probe skips that set, and MCP reports `expectation: retired`.

## What is checked

Every 5 minutes the oneshot `anchor-fault-alarm.service` runs `ops/fault_alarm/probe.py`. The only process call is `systemctl show` on names taken from `anchor-backend/app/mcp/inventory.py`, plus three units that inventory classifies but does not put on the default allowlist.

| Check | Fault when |
| --- | --- |
| Long-running services | `ActiveState` is not `active`, or the unit is not loaded. The list is `RECOMMENDED_SERVICE_UNITS` plus `anchor-mf4-watcher.service` and `anchor-control-mcp.service`. |
| Ledger oneshots | `anchor-official-ledger.service`, `anchor-official-ledger-c6.service`, and `anchor-ledger-readonly-mirror.service` are not loaded, or the last run is not `Result=success` while idle. An in-progress run is healthy. |
| Timers | `RECOMMENDED_TIMER_UNITS` plus `anchor-official-ledger-c6.timer`, except names in `RETIRED_UNITS`. Not loaded, not active, `Result=failed`, never fired while nothing is scheduled, next realtime elapse more than 10 minutes overdue, or no next elapse and the last fire is more than 2 hours old. A future `NextElapseUSecRealtime` means the timer is armed. An active timer with an empty realtime elapse and a non-zero `NextElapseUSecMonotonic` (an `OnUnitActiveSec` / `OnBootSec` timer) is armed. `systemctl show` uses `--timestamp=utc` and the real properties `LastTriggerUSec`, `NextElapseUSecRealtime`, `NextElapseUSecMonotonic`, `InactiveEnterTimestamp`, and `StateChangeTimestamp`. A loaded companion service is held to the same oneshot or long-running rule. Companions in `RETIRED_UNITS` or classed `INTENTIONALLY_DISABLED` are skipped. |
| Backend | `GET http://127.0.0.1:8000/health` is not ok. The URL is the allowlisted probe in `app.mcp.backend_probe`. The body is not copied into the alert. |
| MF4 decision | More than 20 minutes after the latest completed 4h BTC close, `mf4_forward_events.jsonl` has no `SIGNAL_4H` or `SIGNAL_4H_SKIPPED` for that close. |
| Kill switch | State is `OPEN`, or the switch is unreadable. `CLOSED` with `enabled` false is healthy. The reader is `app.mcp.status.read_kill_switch`. |
| Go-live | The post-production guard is not blocked. |
| Live trading | The post-production guard is not blocked. |

`INTENTIONALLY_DISABLED` units are not faults. Names in `RETIRED_UNITS` are skipped the same way. A later retirement is one new line in that tuple. MCP `classify_unit` reports `expectation: retired` and `gates_overall_pass: false`. Host mode still lists those names on `get_services` and `get_timers`, with `healthy: true` and `note: retired`, and the real `systemctl show` properties stay on the record. An older drop-in that still names a retired unit does not make it a fault. The current set is `project-anchor-post-production-monitoring.service` and `.timer`. `anchor-fault-alarm.service` and `anchor-fault-alarm.timer` are `AUXILIARY` in the inventory and are not on the PASS allowlist. They are on the host sidecar observe lists (`OBSERVE_SERVICES`, `OBSERVE_TIMERS`), so `get_services` and `get_timers` can see a dead alarm. This alarm does not watch its own units and does not change what gates MCP PASS.

### MF4 decision

The watcher writes one row per completed 4h bar to `/var/lib/anchor-mf4-watcher/mf4_forward_events.jsonl` (`MF4_OUT_DIR`). A decision is `event_type` `SIGNAL_4H` or `SIGNAL_4H_SKIPPED` whose `bar4h_close_utc` or `signal_available_at` equals the close. Closes are UTC instants on a 14400-second grid (`00:00`, `04:00`, `08:00`, `12:00`, `16:00`, `20:00`). The probe reads the tail of that file and does not follow symlinks. The 20 minutes after a close are grace for that bar. During grace the probe judges the previous close (that close minus 14400 seconds), so a watcher that is still dead across the boundary does not get a recovery. An open `mf4:decision` fault clears only when the close being judged has a decision. A missing or sealed path for that close is a fault. The sealed ledger is not opened.

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

Keys are `EVAL_WEBHOOK_URL`, `EVAL_WEBHOOK_KEY`, `EVAL_WEBHOOK_KEY_HEADER` (default `Authorization`), and `EVAL_WEBHOOK_KEY_FORMAT` (default `Bearer {key}`). One POST, 10 second timeout. Redirects are refused, so `Authorization` is not sent to another host. The first post that does not succeed stops that run. Each successful post is written to the dedupe file before the next post, so a `TimeoutStartSec=120` kill does not repeat a post that already succeeded. The next timer run retries what was not saved. The URL, the key, and the header value are not written to the payload, the state file, or the journal line.

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
| `selftest` | Manual `--send-test`. `state` is `test` and `severity` is `info`. Not a fault, and it does not change dedupe state. |

## Host command sequence

Run these on the Vultr host, in this order. This repository change does not run them.

1. Dry-run. `fault_count` must be `0` before the timer is allowed to post. On a machine that is not the host, missing units show up as faults. That is the same detection the timer uses.

```bash
cd /root/project-anchor
PYTHONPATH=.:anchor-backend python3 ops/fault_alarm/probe.py --dry-run \
  --repo-root /root/project-anchor \
  --mf4-dir /var/lib/anchor-mf4-watcher \
  --state-dir /tmp/anchor-fault-alarm-dry-run
```

`--dry-run` prints the JSON that would be posted. It does not write dedupe state and does not open a socket to the webhook.

2. Install the units. This enables the timer for the next boot and does not start it, so install does not post.

```bash
cd /root/project-anchor
sudo ./ops/fault_alarm/install_fault_alarm.sh
```

The script copies the unit files into `/etc/systemd/system`, rewrites the `/root/project-anchor` prefix when the checkout path differs, reloads systemd, and runs `systemctl enable anchor-fault-alarm.timer` without starting it. It does not print the webhook file. It refuses a unit directory under the sealed ledger paths. `ANCHOR_FAULT_START_NOW=1` is optional: the script dry-runs first and starts the timer only when `fault_count` is `0`.

3. Send one test alert. This does not read or write `/var/lib/anchor-fault-alarm/fault_alarm_state.json`.

```bash
cd /root/project-anchor
sudo PYTHONPATH=.:anchor-backend python3 ops/fault_alarm/probe.py --send-test
```

The receiver should see one object with `type` `anchor_fault`, `check` `selftest`, `state` `test`, and `severity` `info`. `source` is `anchor-fault-alarm`. The stdout line is `SELFTEST=SENT`. A missing credential prints `SELFTEST=NOT_SENT` and does not include the URL or the key. `--send-test --dry-run` prints that object and does not post.

4. Start the timer, then confirm the oneshot finished cleanly.

```bash
sudo systemctl start anchor-fault-alarm.timer
sudo systemctl start anchor-fault-alarm.service
systemctl show anchor-fault-alarm.service -p Result --value
```

`Result` must be `success`. Then:

```bash
systemd-analyze verify /etc/systemd/system/anchor-fault-alarm.service /etc/systemd/system/anchor-fault-alarm.timer
systemctl status anchor-fault-alarm.timer --no-pager
systemctl list-timers anchor-fault-alarm.timer --no-pager
```

Journal lines look like `FAULT_ALARM faults=0 sent=0 recovered=0`. A delivery problem is `delivery skipped credentials_missing` or `delivery failed network_error`. Those lines do not include the URL or the key.

The service uses `ProtectHome=tmpfs` so `BindReadOnlyPaths=/root/project-anchor` is visible inside the sandbox. `CapabilityBoundingSet=CAP_DAC_READ_SEARCH` is the only capability kept above the sandbox. `systemd-analyze verify` checks the unit text; it does not start the service. The `Result=success` check is the acceptance step after a real start.

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
systemd-analyze verify ops/fault_alarm/anchor-fault-alarm.service ops/fault_alarm/anchor-fault-alarm.timer
```

## Out of scope

No restarts, no database writes, no orders, no exchange calls, no edits to Line A, the legacy equity CSV, the governance register, or the PASS LINE freeze record. `project-anchor-post-production-monitoring.timer` and `.service` were retired on 2026-10-24 and are not watched.

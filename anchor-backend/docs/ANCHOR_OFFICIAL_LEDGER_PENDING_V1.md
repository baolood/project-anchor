# ANCHOR_OFFICIAL_LEDGER_PENDING_V1

The Official V2 fill rule is unchanged. `resolve_fill_bar` selects the first 1h bar that opens after `signal_available_at`. Live signals are published at minute :05, so that bar opens on the next hour. The fill price is that bar's `open` string. The open is read only after `fill bar open + 1h <= now` and the closed candle is present. High, low, and close are not fill prices.

This repository change does not rewrite or delete ledger history. Rows already in `anchor_fake_fill_ledger_v2_official.jsonl` stay byte for byte. New rows are appended.

## One pending row after an explicit instant

`ANCHOR_OFFICIAL_LEDGER_PENDING_POLICY_EFFECTIVE_AT` is the instant at which the new pending policy starts. Unset, the writer keeps the current behavior: each retry in an observation appends a `PENDING_NEXT_BAR` row.

At and after that instant, one observation appends at most one `PENDING_NEXT_BAR` row:

| `pending_reason` | When |
| --- | --- |
| `BAR_NOT_YET_CLOSED` | `fill bar open + 1h > now`. The bar is not in the closed-candle data yet, so its open is not read. |
| `DATA_GAP` | The bar should already be closed, and the candle is missing. |

Retries of that same observation are appended to `anchor_fake_fill_ledger_v2_official.run.log` next to the ledger. They are not ledger rows. A fill still uses `planned_fill`, so `fill_price` and `fill_time_utc` match the current rule.

Code: `anchor-backend/app/official_ledger/engine.py`.

## Candle-fetch ordering

The ledger timer runs at minute :10. The fill bar that opened on the hour is not in the closed-candle data until the following hour, so a :10 run cannot see a bar that has not closed. Running the ledger as soon as candle fetch succeeds removes the extra wait after the bar does close. It does not change the fill price or the fill timestamp.

Examples:

- [`systemd/anchor-candle-fetch.service.d/start-official-ledger.conf.example`](systemd/anchor-candle-fetch.service.d/start-official-ledger.conf.example) adds `OnSuccess=anchor-official-ledger.service` on the candle-fetch unit.
- [`systemd/anchor-official-ledger.service.d/after-candle-fetch.conf.example`](systemd/anchor-official-ledger.service.d/after-candle-fetch.conf.example) adds `After=anchor-candle-fetch.service` on the ledger unit.
- [`systemd/anchor-official-ledger.service.d/pending-policy.conf.example`](systemd/anchor-official-ledger.service.d/pending-policy.conf.example) sets the effective timestamp.

Confirm the installed candle-fetch unit name before copying the drop-in. If it is not `anchor-candle-fetch.service`, substitute that name and nothing else. `OnSuccess=` can be set more than once. These drop-ins do not set `User=`, `DynamicUser=`, `StateDirectory=`, and they do not `chmod` or `setfacl` anything.

The mirror timer no longer fires at minute :10, and the mirror waits until the source size and mtime have been unchanged for 2 seconds. See [`ANCHOR_LEDGER_READONLY_MIRROR_V1.md`](ANCHOR_LEDGER_READONLY_MIRROR_V1.md).

## Deploy

Do not run this from the pull request. Never run `chmod` or `setfacl` on `/var/lib/private`, `/var/lib/private/anchor-official-ledger-20261010`, `/var/lib/anchor-official-ledger-20261010`, or any path under those directories. Do not delete or edit existing ledger lines.

1. Confirm the StateDirectory mode and leave it:

```bash
stat -c '%a %U %G %n' /var/lib/private /var/lib/private/anchor-official-ledger-20261010 /var/lib/anchor-official-ledger-20261010
systemctl cat anchor-official-ledger.service
systemctl cat anchor-candle-fetch.service
```

2. Install this tree on the Python path `anchor-official-ledger.service` already uses. The process calls `resolve_fill_bar` for the fill price and `commit_observation` for a signal that is not filled yet. Do not replace `ExecStart`. Do not change the ledger unit's `User=`, `DynamicUser=`, `StateDirectory=`, or any mode or ACL.

3. Choose an explicit effective timestamp. Replace the placeholder below. The sample value is `2026-10-13T00:00:00Z` only so the example file has a concrete instant.

```bash
install -d /etc/systemd/system/anchor-official-ledger.service.d
install -d /etc/systemd/system/anchor-candle-fetch.service.d
install -m 0644 anchor-backend/docs/systemd/anchor-official-ledger.service.d/after-candle-fetch.conf.example /etc/systemd/system/anchor-official-ledger.service.d/after-candle-fetch.conf
install -m 0644 anchor-backend/docs/systemd/anchor-candle-fetch.service.d/start-official-ledger.conf.example /etc/systemd/system/anchor-candle-fetch.service.d/start-official-ledger.conf
install -m 0644 anchor-backend/docs/systemd/anchor-official-ledger.service.d/pending-policy.conf.example /etc/systemd/system/anchor-official-ledger.service.d/pending-policy.conf
```

Edit only the timestamp in `pending-policy.conf` if `2026-10-13T00:00:00Z` is not the chosen instant. Edit the candle unit name in the two ordering drop-ins if the installed unit is not `anchor-candle-fetch.service`.

4. Install the updated mirror timer so it no longer uses minute 10, then reload. The next ledger start picks up the drop-ins. Do not restart `anchor-official-ledger.service` in order to change directory permissions.

```bash
install -m 0644 anchor-backend/docs/systemd/anchor-ledger-readonly-mirror.timer.example /etc/systemd/system/anchor-ledger-readonly-mirror.timer
systemctl daemon-reload
systemctl restart anchor-ledger-readonly-mirror.timer
stat -c '%a %U %G %n' /var/lib/private /var/lib/private/anchor-official-ledger-20261010 /var/lib/anchor-official-ledger-20261010
```

The StateDirectory lines must still be mode `0700`.

## Rollback

These steps also never `chmod` or `setfacl` the ledger StateDirectory, and they do not delete or rewrite the ledger file.

```bash
rm -f /etc/systemd/system/anchor-official-ledger.service.d/after-candle-fetch.conf
rm -f /etc/systemd/system/anchor-official-ledger.service.d/pending-policy.conf
rm -f /etc/systemd/system/anchor-candle-fetch.service.d/start-official-ledger.conf
rmdir /etc/systemd/system/anchor-candle-fetch.service.d 2>/dev/null || true
systemctl daemon-reload
```

Unset `ANCHOR_OFFICIAL_LEDGER_PENDING_POLICY_EFFECTIVE_AT` by removing `pending-policy.conf`, which the commands above do. The following observations use the previous retry behavior. Rows written while the policy was on stay in the ledger.

Restore the previous mirror timer from git history if minute 10 should be scheduled again, then `systemctl daemon-reload` and restart only `anchor-ledger-readonly-mirror.timer`.

Do not remove `/var/lib/private`, `/var/lib/private/anchor-official-ledger-20261010`, or `/var/lib/anchor-official-ledger-20261010`. Do not remove `anchor_fake_fill_ledger_v2_official.jsonl`. The run log may be removed; it is not the ledger.

## Local check

```bash
cd /path/to/project-anchor
PYTHONPATH=anchor-backend python3 -m unittest discover -s anchor-backend/tests -p 'test_official_ledger_fill_rule.py'
PYTHONPATH=anchor-backend python3 -m unittest discover -s anchor-backend/tests -p 'test_anchor_ledger_readonly_mirror.py'
```

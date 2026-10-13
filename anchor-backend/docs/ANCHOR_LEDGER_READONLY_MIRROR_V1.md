# ANCHOR_LEDGER_READONLY_MIRROR_V1

`anchor-official-ledger.service` uses systemd `DynamicUser=` and `StateDirectory=`. That state directory must stay mode `0700` and owned by the dynamic user. An ACL on `/var/lib/private` and the ledger root changed the displayed mode to `0710`. systemd then refused to start the unit, and one hourly run did not write.

The ACL is removed and the directories are back to `0700`. `anchor-mcp` cannot read that tree. Do not put the ACL back. Do not `chmod` the StateDirectory to make it readable.

`anchor-ledger-readonly-mirror.service` is a separate root oneshot. It opens one source file read-only and copies it to a new directory the MCP is allowed to read. It does not change the source mode, owner, ACL, or bytes.

## What is copied

Source, under the ledger root (`/var/lib/anchor-official-ledger-20261010`, which is a symlink to `/var/lib/private/anchor-official-ledger-20261010`):

```text
affl-v2-official-ledger/out/anchor_fake_fill_ledger_v2_official.jsonl
```

The mirror also copies `events.jsonl` when that file is a regular file at the ledger root, and it writes `run-boundaries.jsonl`. A committed line in `events.jsonl` carries `run_seq` and cumulative `ledger_events`. Run N owns ledger lines `(ledger_events of run N-1, ledger_events of run N]`. A boundary line records that span and the committed `at`. The before-snapshot `runs/run-NNNNNN/before/affl-v2-official-ledger/out/anchor_fake_fill_ledger_v2_official.jsonl` is opened read-only, last line only, and is not copied. It is a cross-check: when the file exists, its last id must be the last id of the previous run (an empty file for run 1). A mismatch, or a `run_seq` series that does not start at 1 and stay contiguous, does not publish `run-boundaries.jsonl`. The flat path `runs/run-NNNNNN/before/anchor_fake_fill_ledger_v2_official.jsonl` is not read. `baseline/`, a same-named file at the top of the root, and `BLOCKED.json` are not copied. The same 2 second stability rule applies to the live ledger, to `events.jsonl`, and to each nested before-snapshot that is read: if any of them is still changing after 30 seconds, the copier skips and does not publish a partial mirror. The timer is `OnCalendar=*:00,20,30,40,50`. The copy runs only after the watched files have been unchanged for 2 seconds.

Destination directory: `/var/lib/anchor-ledger-mirror`

| Path | Mode | Owner |
| --- | --- | --- |
| `/var/lib/anchor-ledger-mirror/` | `0750` | `root:anchor-mcp` |
| `anchor_fake_fill_ledger_v2_official.jsonl` | `0640` | `root:anchor-mcp` |
| `anchor_fake_fill_ledger_v2_official.jsonl.sha256` | `0640` | `root:anchor-mcp` |
| `anchor_fake_fill_ledger_v2_official.jsonl.meta.json` | `0640` | `root:anchor-mcp` |
| `events.jsonl` and `events.jsonl.sha256`, when the source file exists | `0640` | `root:anchor-mcp` |
| `run-boundaries.jsonl` and `run-boundaries.jsonl.sha256`, when `events.jsonl` is a contiguous `run_seq` index from 1 and every present before-snapshot matches | `0640` | `root:anchor-mcp` |

The `.sha256` file is `sha256sum` form: 64 hex digits, two spaces, the ledger basename, and a newline. The metadata JSON has `source_mtime` (UTC), `source_size` (bytes), and `copied_at` (UTC).

The copy writes a temp file in the destination directory, `fsync`s it, and `rename`s it into place. The source is opened `O_RDONLY|O_NOFOLLOW`. Before that open, the copier waits until the source size and mtime have stayed unchanged for 2 seconds, and it skips the copy if they are still changing after 30 seconds. The destination must not sit inside the source tree, and the source must not sit inside the destination.

## Units

Examples, rendered by `app.mcp.ledger_mirror`:

- [`systemd/anchor-ledger-readonly-mirror.service.example`](systemd/anchor-ledger-readonly-mirror.service.example)
- [`systemd/anchor-ledger-readonly-mirror.timer.example`](systemd/anchor-ledger-readonly-mirror.timer.example)
- [`systemd/anchor-official-ledger.service.d/readonly-mirror.conf.example`](systemd/anchor-official-ledger.service.d/readonly-mirror.conf.example)

The service and the timer are ordered `After=anchor-official-ledger.service`. The timer runs `OnCalendar=*:00,20,30,40,50`, `OnBootSec=2min`, `Persistent=true`. Minute 10 is omitted because that is when `anchor-official-ledger.service` writes the source file. The drop-in adds only `OnSuccess=anchor-ledger-readonly-mirror.service` on the ledger unit so a completed ledger run starts a copy, which then waits for the source to stay unchanged for 2 seconds. `OnSuccess=` can be set more than once; this drop-in adds a dependency and does not replace another `OnSuccess=`.

The service is `User=root`, `ProtectSystem=strict`, `ReadOnlyPaths=` on both ledger roots, `ReadWritePaths=/var/lib/anchor-ledger-mirror`, `PrivateNetwork=yes`, and `RestrictAddressFamilies=AF_UNIX`. It does not set `StateDirectory=` or `DynamicUser=`. It does not `chmod` or `setfacl` the ledger StateDirectory.

## MCP

`ANCHOR_CONTROL_MCP_LEDGER_DIR` allowlist is only `/var/lib/anchor-ledger-mirror`. The reader checks the `.sha256` sidecar before it summarizes. A missing sidecar, a symlink, a bad line, or a digest mismatch returns `available: false` and does not include `hash_chain_head`.

`mirror_stale` is true when `copied_at` is missing or when `mirror_age_sec` is greater than 5400 (90 minutes). An age of exactly 5400 is not stale. A stale mirror with a matching hash stays `available: true`. `run_readonly_healthcheck` still treats `available: true` as the ledger gate.

## Deploy

Do not run this from the pull request. A later reviewed host change does the following, and never runs `chmod` or `setfacl` on `/var/lib/private`, `/var/lib/private/anchor-official-ledger-20261010`, `/var/lib/anchor-official-ledger-20261010`, or any path under those directories.

1. Confirm the StateDirectory is still mode `0700` before changing anything else:

```bash
stat -c '%a %U %G %n' /var/lib/private /var/lib/private/anchor-official-ledger-20261010 /var/lib/anchor-official-ledger-20261010
systemctl show anchor-official-ledger.service -p ActiveState -p Result -p StateDirectory -p FragmentPath
```

Leave those modes as they are. Do not restart `anchor-official-ledger.service` to make the MCP able to read.

2. Create only the new mirror directory. The group `anchor-mcp` must already exist.

```bash
install -d -o root -g anchor-mcp -m 0750 /var/lib/anchor-ledger-mirror
```

3. Install the three example units to:

```text
/etc/systemd/system/anchor-ledger-readonly-mirror.service
/etc/systemd/system/anchor-ledger-readonly-mirror.timer
/etc/systemd/system/anchor-official-ledger.service.d/readonly-mirror.conf
```

The drop-in file must contain only the `[Unit]` and `OnSuccess=` lines from the example. Do not edit the ledger unit's `User=`, `DynamicUser=`, `StateDirectory=`, or any permission setting.

4. Point the MCP at the mirror. The example `anchor-control-mcp.service` sets `Environment=ANCHOR_CONTROL_MCP_LEDGER_DIR=/var/lib/anchor-ledger-mirror`. `EnvironmentFile=` is later in that unit and overrides the unit line. Leave the variable unset in `/etc/project-anchor/anchor-control-mcp.env` unless that file sets it to `/var/lib/anchor-ledger-mirror`. Do not set it to the StateDirectory.

5. Reload and start the mirror. Restart only the MCP unit.

```bash
systemctl daemon-reload
systemctl enable --now anchor-ledger-readonly-mirror.timer
systemctl start anchor-ledger-readonly-mirror.service
systemctl restart anchor-control-mcp.service
```

6. Confirm the copy and confirm the StateDirectory was not touched:

```bash
stat -c '%a %U %G %n' /var/lib/anchor-ledger-mirror /var/lib/anchor-ledger-mirror/anchor_fake_fill_ledger_v2_official.jsonl
sha256sum -c /var/lib/anchor-ledger-mirror/anchor_fake_fill_ledger_v2_official.jsonl.sha256
stat -c '%a %U %G %n' /var/lib/private /var/lib/private/anchor-official-ledger-20261010 /var/lib/anchor-official-ledger-20261010
systemctl show anchor-official-ledger.service -p ActiveState -p Result -p StateDirectory
```

The StateDirectory lines must still be mode `0700`. The next scheduled ledger run is the confirmation that `DynamicUser` still accepts that directory. The `OnSuccess=` drop-in starts the mirror after that run. The 10-minute timer covers the gap between hourly ledger runs.

## Rollback

These steps also never `chmod` or `setfacl` the ledger StateDirectory. Do not re-apply an ACL so the MCP can read `0700` again. With this code the safe unread state is `ledger_available: false`.

```bash
systemctl disable --now anchor-ledger-readonly-mirror.timer
systemctl disable --now anchor-ledger-readonly-mirror.service
rm -f /etc/systemd/system/anchor-official-ledger.service.d/readonly-mirror.conf
rmdir /etc/systemd/system/anchor-official-ledger.service.d 2>/dev/null || true
rm -f /etc/systemd/system/anchor-ledger-readonly-mirror.service /etc/systemd/system/anchor-ledger-readonly-mirror.timer
systemctl daemon-reload
```

`rmdir` removes the drop-in directory only when it is empty. Leave any other drop-in in place.

Unset `ANCHOR_CONTROL_MCP_LEDGER_DIR` in `/etc/project-anchor/anchor-control-mcp.env` if it was set there, and restart `anchor-control-mcp.service` so it returns to report JSON. Do not point that variable back at the StateDirectory. That path is not allowlisted, and mode `0700` is not readable by `anchor-mcp`.

Optional, and only this path:

```bash
rm -rf /var/lib/anchor-ledger-mirror
```

Do not remove `/var/lib/private`, `/var/lib/private/anchor-official-ledger-20261010`, or `/var/lib/anchor-official-ledger-20261010`.

## Local check

```bash
cd /path/to/project-anchor
PYTHONPATH=anchor-backend python3 -m unittest discover -s anchor-backend/tests -p 'test_anchor_ledger_readonly_mirror.py'
PYTHONPATH=anchor-backend python3 -m unittest discover -s anchor-backend/tests -p 'test_anchor_control_mcp_official_ledger.py'
```

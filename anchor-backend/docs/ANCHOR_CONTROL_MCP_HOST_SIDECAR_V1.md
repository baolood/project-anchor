# ANCHOR_CONTROL_MCP_HOST_SIDECAR_V1

The FastAPI backend runs in Docker and publishes `127.0.0.1:8000`. That process cannot reliably see host systemd. The read-only MCP control surface for host status therefore runs as its own unit, `anchor-control-mcp.service`, on `127.0.0.1:8021`.

The 2026-09-29 read-only Vultr inventory shows `project-anchor-payment-webhook.service` already bound to `127.0.0.1:8001`. The sidecar does not use that port.

This change does not deploy to Vultr, does not edit live Nginx, does not change `anchor-backend/docker-compose.yml`, and does not merge itself.

## Process

- Unit example: [`systemd/anchor-control-mcp.service.example`](systemd/anchor-control-mcp.service.example)
- User and group: `anchor-mcp` (the process refuses to start as root)
- Supplementary group: `systemd-journal` so `journalctl -p err` can read allowlisted unit logs
- Listen address: `127.0.0.1:8021` only. Any other `ANCHOR_CONTROL_MCP_BIND` value exits before listen.
- App: `python3 -m app.mcp.host_sidecar` mounts only `POST /mcp`. It does not mount trading, account, or ops-write routes.
- Credential file, outside git: `/etc/project-anchor/anchor-control-mcp.env` (`ANCHOR_CONTROL_MCP_TOKEN`, and `REDIS_URL` for the existing read-only kill-switch GET). systemd reads that file before dropping privileges. Do not commit it.

The tools are the same tools as [`ANCHOR_CONTROL_MCP_V1.md`](ANCHOR_CONTROL_MCP_V1.md), including `get_mf4_status` and `get_eval_state`. Those two read `ANCHOR_CONTROL_MCP_MF4_DIR` only when it is set, and they do not open Line A. systemd access stays the fixed argv allowlist (`systemctl show`, `journalctl -u <service> -p err`). Report JSON stays inside the allowlisted reports directory.

## What the sidecar may do

- `systemctl show` and `journalctl -p err` for allowlisted unit names
- Read allowlisted report JSON and `docs/GO_LIVE_CHECKLIST.md`
- Read Official V2 ledger files when `ANCHOR_CONTROL_MCP_LEDGER_DIR` names the allowlisted mirror directory `/var/lib/anchor-ledger-mirror`. The sidecar does not open the ledger StateDirectory. Opens are read-only. The sidecar does not write the mirror. See [`ANCHOR_LEDGER_READONLY_MIRROR_V1.md`](ANCHOR_LEDGER_READONLY_MIRROR_V1.md).
- Read the C6 series equity CSV when `ANCHOR_CONTROL_MCP_C6_SERIES_DIR` is set, and return only the compact `c6_series` block on `get_ledger_summary`. The drop-in template `docs/templates/anchor-control-mcp.service.d/30-c6-series.conf` is what exposes `/var/lib/anchor-passline` read-only. This change does not install that drop-in. The reader does not write the series and does not open Line A.
- Optionally `GET http://127.0.0.1:8000/health` and `GET http://127.0.0.1:8000/ops/state`

`/health` gates the host health check. `/ops/state` is reduced to booleans (`kill_switch`, `worker_heartbeat`, `worker_panic` present or not) and does not gate PASS. Response bodies are not returned. Redirects are not followed. No other URL is requested. `ANCHOR_CONTROL_MCP_BACKEND_PROBE=0` turns the probe off.

## What the sidecar must not do

- Mount or open the Docker socket, or join the `docker` group
- SSH, or any shell other than the two allowlisted commands
- Account, order, trade, or withdrawal calls
- Database writes, including Postgres
- `systemctl start`, `stop`, `restart`, or `reload`
- Read `.env`, API keys, or the MCP token back out through a tool

`anchor-backend/docker-compose.yml` stays on `127.0.0.1:8000:8000`. The in-container `POST /mcp` route is unchanged and is not the host systemd view. Do not point public `/mcp` at port 8000.

## Nginx example

[`nginx/anchor-control-mcp.location.example.conf`](nginx/anchor-control-mcp.location.example.conf) proxies `location = /mcp` to `http://127.0.0.1:8021/mcp` and forwards `Authorization`. That file is an example. Do not install it on a live host from this change.

## Inventory classification

Classes:

| Class | Gates overall PASS |
| --- | --- |
| `CORE_RUNTIME` | yes |
| `EVALUATION` | no |
| `AUXILIARY` | no |
| `INTENTIONALLY_DISABLED` | no |

Only `CORE_RUNTIME` gates the process, service, and timer portions of `run_readonly_healthcheck`. An empty core-timer set passes the timer check (no core timer is required). An empty core-service set is `UNKNOWN` and is not PASS. `INTENTIONALLY_DISABLED` is not required to be active. If that unit is active anyway, the payload notes `active_while_intentionally_disabled` and PASS is still not blocked by it.

The same health check still requires the existing non-unit gates: kill switch `CLOSED` from a successful Redis read, an observation result of `PASS`, `OK`, or `PASS_REPO_RECORDED_ONLY`, a ledger summary with `available` true, and no sanitized errors from core units. On the host sidecar, enabled `backend_http` (`/health` on `127.0.0.1:8000`) is also required. When `ANCHOR_CONTROL_MCP_LEDGER_DIR` is set, the ledger gate is the Official V2 directory and does not fall back to report JSON.

Classes below started from the 2026-09-29 Vultr read-only inventory (host `vultr`). The timer allowlist was replaced on 2026-10-23 by the founder drop-in already live on that host. This repository change records that list. It does not install the drop-in, restart the sidecar, or edit the ledger StateDirectory. Docker container names are not systemd units. The backend on `127.0.0.1:8000` is covered by the HTTP probe, not by `docker.service`. An allowlisted name that matches nothing here stays `CORE_RUNTIME`. The ledger units below are classified so they do not become that fallback.

| Unit | Class | Inventory role |
| --- | --- | --- |
| `nginx.service` | `CORE_RUNTIME` | Enabled TLS edge. The ops site proxies to the Docker backend |
| `project-anchor-commercial-api.service` | `AUXILIARY` | Commercial self-serve API on `127.0.0.1:8010` |
| `project-anchor-payment-webhook.service` | `AUXILIARY` | Payment webhook adapter on `127.0.0.1:8001` |
| `project-anchor-whisper.service` | `AUXILIARY` | Voice server on `127.0.0.1:8088` |
| `project-anchor-word-converter.service` | `AUXILIARY` | Document converter on `127.0.0.1:8791` |
| `project-anchor-kraken-public-shadow-paper-v1-1.service` and `.timer` | `EVALUATION` | Disabled on the host 2026-10-23. Not in the default lists |
| `project-anchor-evidence-reporter-v1.service` and `.timer` | `AUXILIARY` | Removed from the 2026-10-23 default lists |
| `project-anchor-jev-candidate-review-v1.service` and `.timer` | `EVALUATION` | Removed from the 2026-10-23 default lists |
| `project-anchor-jev-forward-shadow-v1.service` and `.timer` | `EVALUATION` | Removed from the 2026-10-23 default lists |
| `project-anchor-jev-forward-shadow-v2.service` | `INTENTIONALLY_DISABLED` | Observed. Not required for PASS |
| `project-anchor-jev-forward-shadow-v2.timer` | `EVALUATION` | Official Ledger feed. On the 2026-10-23 default timer list. Does not gate PASS |
| `project-anchor-kraken-forward.service` | `EVALUATION` | Forward collector. Unit file disabled; optional oneshot |
| `project-anchor-kraken-forward.timer` | `EVALUATION` | Still on the default timer list |
| `project-anchor-post-production-monitoring.service` and `.timer` | `AUXILIARY` | Read-only monitoring refresh. Timer stays on the default list |
| `anchor-official-ledger.service` and `.timer` | `EVALUATION` | Official Ledger writer. Timer is on the default list. Oneshot and timer stay `expectation: observed` and do not gate PASS |
| `anchor-ledger-readonly-mirror.service` and `.timer` | `EVALUATION` | Read-only mirror of the ledger file. Timer is on the default list. Oneshot and timer stay `expectation: observed` and do not gate PASS |
| `anchor-official-ledger-c6.service` and `.timer` | `EVALUATION` | C6 pass-line series recorder. Not on the default allowlist. The host drop-in template adds them. Hourly at minute 13 UTC. Does not gate PASS |
| `anchor-mf4-watcher.service` | `EVALUATION` | MF4 host watcher. Public PF_XBTUSD only. Not on the default allowlist. Does not gate PASS |
| `project-anchor-kraken-public-shadow-paper-v1-1-monitor.service` | `EVALUATION` | Failed at inventory time. Excluded from the default lists |
| `project-anchor-kraken-turtle-eth-1h-shadow.timer` | `EVALUATION` | Inactive historical timer. Excluded from the default lists |
| `docker.service` | `AUXILIARY` | Not an inventoried systemd control target |

Name rules cover the same roles when the exact unit is not in the table: `whisper`, `word-converter`, `commercial`, and `payment` are `AUXILIARY`. `shadow`, `paper`, `turtle`, `track-b`, `prop-pe`, and `recovery` are `EVALUATION`. `official-ledger` and `ledger-readonly-mirror` are `EVALUATION`. `jev-forward-shadow-v2` stays `INTENTIONALLY_DISABLED` unless the exact timer row above matches first.

Journal errors are collected only for `CORE_RUNTIME` services. On this inventory that is `nginx.service`. A disabled, evaluation, or auxiliary unit cannot fail `recent_errors`.

## Recommended allowlists

These match the inventory's production lists. Spaces match the inventory text. Commas are equivalent and are what the example unit uses, because systemd treats an unquoted space as another `Environment=` assignment.

```bash
ANCHOR_CONTROL_MCP_SERVICE_UNITS="nginx.service project-anchor-commercial-api.service project-anchor-payment-webhook.service project-anchor-whisper.service project-anchor-word-converter.service"
ANCHOR_CONTROL_MCP_TIMER_UNITS="project-anchor-post-production-monitoring.timer project-anchor-kraken-forward.timer project-anchor-jev-forward-shadow-v2.timer anchor-official-ledger.timer anchor-ledger-readonly-mirror.timer"
```

Of those services, only `nginx.service` gates PASS. The four product services are read and classified `AUXILIARY`. None of the recommended timers gate PASS. `project-anchor-jev-forward-shadow-v2.timer` stays on the list because it is the Official Ledger feed. `anchor-official-ledger.timer` and `anchor-ledger-readonly-mirror.timer` are `EVALUATION` with `expectation: observed`. An idle oneshot or an inactive timer in that class does not fail PASS. `project-anchor-jev-forward-shadow-v2.service` is observed and does not gate PASS. Shadow paper v1.1, evidence reporter v1, JEV forward shadow v1, and JEV candidate review v1 are classified and left out of the default lists. The failed shadow-paper monitor and the inactive turtle timer stay out as well.

The sidecar does not read `RECOMMENDED_TIMER_UNITS` on each request when `ANCHOR_CONTROL_MCP_TIMER_UNITS` is set. `configured_units` uses that environment value, and uses `HOST_DEFAULT_TIMERS` (the same tuple) only when the variable is empty or invalid. Host mode then appends any `OBSERVE_TIMERS` name that is not already selected, up to 16 names. `anchor-fault-alarm.service` and `anchor-fault-alarm.timer` are on those observe lists and are `AUXILIARY`, so a read-only check can see a dead alarm without changing PASS. systemd applies a drop-in `Environment=` after the main unit file, and `EnvironmentFile=` overrides `Environment=` when the file sets the same key. The live host drop-in `anchor-control-mcp.service.d/20-timer-allowlist.conf` therefore supplies the running process. A process that still imports the previous observe tuple keeps showing the retired timers after that drop-in list. `render_service_unit()` writes `RECOMMENDED_TIMER_UNITS` into the example unit. This sync keeps the next render from putting the retired timers back, and it stops appending them. `get_timers` also reports `recommended_timer_units` from the Python tuple, separate from the units it actually shows. Unclassified names in that shown list are `CORE_RUNTIME`. The ledger rows above exist so those allowlisted timers do not gate PASS.

Reports directory from the inventory: `/var/lib/project-anchor/reports`.

Official V2 ledger directory named by the example unit: `/var/lib/anchor-ledger-mirror`. That directory is a root-owned copy. The writer still stores the live file at `affl-v2-official-ledger/out/anchor_fake_fill_ledger_v2_official.jsonl` under `/var/lib/anchor-official-ledger-20261010` (a symlink to `/var/lib/private/anchor-official-ledger-20261010`). The MCP allowlist does not include that StateDirectory. The writer is `anchor-official-ledger.service` and its timer. This repository change does not install that unit, restart it, or change its directory mode.

`get_services` and `get_timers` repeat `recommended_service_units`, `recommended_timer_units`, `gating_classes`, and `non_gating_classes` when `ANCHOR_CONTROL_MCP_HOST_SIDECAR=1`.

The in-container MCP does not set that flag. Its default units remain `project-anchor-post-production-monitoring.service` and `.timer`.

## Later operator steps

Do not run these from this pull request. They are the reviewed install shape for a later host change.

1. Create system user `anchor-mcp` with a nologin shell. Do not add it to the `docker` group.
2. Give that user read access to the reports directory and `docs/GO_LIVE_CHECKLIST.md`. Do not run the sidecar as root to work around a `/root` checkout mode.
3. Install the existing `anchor-backend` Python dependencies for `/usr/bin/python3` (FastAPI, uvicorn, redis). The sidecar imports those modules. It does not need a Docker client.
4. Create `/etc/project-anchor/anchor-control-mcp.env` mode `0600`, owned by root, containing `ANCHOR_CONTROL_MCP_TOKEN` and `REDIS_URL=redis://127.0.0.1:6379/0`. No database URL, API key, or exchange secret.
5. Install the example unit under `/etc/systemd/system/anchor-control-mcp.service`, then `systemctl daemon-reload` and enable it in a separate reviewed change. The example sets `ANCHOR_CONTROL_MCP_LEDGER_DIR=/var/lib/anchor-ledger-mirror`. `EnvironmentFile=` is later in the unit, so a value in `/etc/project-anchor/anchor-control-mcp.env` overrides that line. Leave the variable unset in the env file unless it is set to `/var/lib/anchor-ledger-mirror`. Do not set it to the ledger StateDirectory.
6. Install the read-only mirror from [`ANCHOR_LEDGER_READONLY_MIRROR_V1.md`](ANCHOR_LEDGER_READONLY_MIRROR_V1.md). Do not `chmod` or `setfacl` `/var/lib/private`, `/var/lib/private/anchor-official-ledger-20261010`, or `/var/lib/anchor-official-ledger-20261010`. An ACL on that DynamicUser StateDirectory changed the displayed mode to `0710` and `anchor-official-ledger.service` then refused to start. The mirror directory is a new path, mode `0750` `root:anchor-mcp`. Restart `anchor-control-mcp.service` only in that later reviewed change, after the mirror unit has copied a file and the MCP unit points at the mirror. Do not restart `anchor-official-ledger.service` to make the MCP able to read.

Render the example without installing it:

```bash
cd /path/to/project-anchor
python3 scripts/render_anchor_control_mcp_host_unit.py
```

## Local check

```bash
cd /path/to/project-anchor
PYTHONPATH=anchor-backend python3 -m unittest discover -s anchor-backend/tests -p 'test_anchor_control_mcp*.py'
```

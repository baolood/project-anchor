# ANCHOR_CONTROL_MCP_HOST_SIDECAR_V1

The FastAPI backend runs in Docker and publishes `127.0.0.1:8000`. That process cannot reliably see host systemd. The read-only MCP control surface for host status therefore runs as its own unit, `anchor-control-mcp.service`, on `127.0.0.1:8001`.

This change does not deploy to Vultr, does not edit live Nginx, does not change `anchor-backend/docker-compose.yml`, and does not merge itself.

## Process

- Unit example: [`systemd/anchor-control-mcp.service.example`](systemd/anchor-control-mcp.service.example)
- User and group: `anchor-mcp` (the process refuses to start as root)
- Supplementary group: `systemd-journal` so `journalctl -p err` can read allowlisted unit logs
- Listen address: `127.0.0.1:8001` only. Any other `ANCHOR_CONTROL_MCP_BIND` value exits before listen.
- App: `python3 -m app.mcp.host_sidecar` mounts only `POST /mcp`. It does not mount trading, account, or ops-write routes.
- Credential file, outside git: `/etc/project-anchor/anchor-control-mcp.env` (`ANCHOR_CONTROL_MCP_TOKEN`, and `REDIS_URL` for the existing read-only kill-switch GET). systemd reads that file before dropping privileges. Do not commit it.

The seven tools are the same tools as [`ANCHOR_CONTROL_MCP_V1.md`](ANCHOR_CONTROL_MCP_V1.md). systemd access stays the fixed argv allowlist (`systemctl show`, `journalctl -u <service> -p err`). Report JSON stays inside the allowlisted reports directory.

## What the sidecar may do

- `systemctl show` and `journalctl -p err` for allowlisted unit names
- Read allowlisted report JSON and `docs/GO_LIVE_CHECKLIST.md`
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

[`nginx/anchor-control-mcp.location.example.conf`](nginx/anchor-control-mcp.location.example.conf) proxies `location = /mcp` to `http://127.0.0.1:8001/mcp` and forwards `Authorization`. That file is an example. Do not install it on a live host from this change.

## Inventory classification

Classes:

| Class | Gates overall PASS |
| --- | --- |
| `CORE_RUNTIME` | yes |
| `EVALUATION` | no |
| `AUXILIARY` | no |
| `INTENTIONALLY_DISABLED` | no |

Only `CORE_RUNTIME` gates the process, service, and timer portions of `run_readonly_healthcheck`. An empty core-timer set passes the timer check (no core timer is required). An empty core-service set is `UNKNOWN` and is not PASS. `INTENTIONALLY_DISABLED` is not required to be active. If that unit is active anyway, the payload notes `active_while_intentionally_disabled` and PASS is still not blocked by it.

The same health check still requires the existing non-unit gates: kill switch `CLOSED` from a successful Redis read, an observation result of `PASS` or `OK`, a ledger file present, and no sanitized errors from core units. On the host sidecar, enabled `backend_http` (`/health` on `127.0.0.1:8000`) is also required.

This table is the founder-note classification plus units this repository installs or depends on. It is not a live `systemctl list-units` capture. Exact filenames for whisper, word-converter, commercial, and payment were not in the repository; those rows are name rules. A matching unit is classified even if an operator adds it to the allowlist. An allowlisted name that matches nothing here stays `CORE_RUNTIME`, so a future Anchor unit still gates PASS until a class is recorded.

| Unit | Class | Role |
| --- | --- | --- |
| `docker.service` | `CORE_RUNTIME` | Host engine for the Docker backend, worker, Postgres, and Redis published on `127.0.0.1` |
| `project-anchor-post-production-monitoring.service` | `AUXILIARY` | Oneshot read-only monitoring refresh |
| `project-anchor-post-production-monitoring.timer` | `AUXILIARY` | Schedules that oneshot |
| `nginx.service` | `AUXILIARY` | Public edge. Not required for loopback runtime health |
| `jev-forward-shadow-v2.service` | `INTENTIONALLY_DISABLED` | Founder note. Inactive or absent does not fail PASS |
| name contains `whisper` | `AUXILIARY` | Founder note. Not core runtime |
| name contains `word-converter` or `word_converter` | `AUXILIARY` | Founder note. Utility, not core runtime |
| name contains `commercial` | `EVALUATION` | Founder note. Evaluation lane, not core runtime |
| name contains `payment` | `EVALUATION` | Founder note. Not justified as core runtime |

The host sidecar also `systemctl show`s the exact rows above (the observe catalog) so `get_services` and `get_timers` can report class. Journal errors are collected only for `CORE_RUNTIME` services, so a disabled or auxiliary unit cannot fail `recent_errors`.

## Recommended allowlists

Set these on the host sidecar, not inside the Docker backend container:

```bash
ANCHOR_CONTROL_MCP_SERVICE_UNITS=docker.service
ANCHOR_CONTROL_MCP_TIMER_UNITS=
```

`get_services` and `get_timers` repeat `recommended_service_units`, `recommended_timer_units`, `gating_classes`, and `non_gating_classes` when `ANCHOR_CONTROL_MCP_HOST_SIDECAR=1`.

The in-container MCP does not set that flag. Its default units remain `project-anchor-post-production-monitoring.service` and `.timer`.

## Later operator steps

Do not run these from this pull request. They are the reviewed install shape for a later host change.

1. Create system user `anchor-mcp` with a nologin shell. Do not add it to the `docker` group.
2. Give that user read access to the reports directory and `docs/GO_LIVE_CHECKLIST.md`. Do not run the sidecar as root to work around a `/root` checkout mode.
3. Install the existing `anchor-backend` Python dependencies for `/usr/bin/python3` (FastAPI, uvicorn, redis). The sidecar imports those modules. It does not need a Docker client.
4. Create `/etc/project-anchor/anchor-control-mcp.env` mode `0600`, owned by root, containing `ANCHOR_CONTROL_MCP_TOKEN` and `REDIS_URL=redis://127.0.0.1:6379/0`. No database URL, API key, or exchange secret.
5. Install the example unit under `/etc/systemd/system/anchor-control-mcp.service`, then `systemctl daemon-reload` and enable it in a separate reviewed change.

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

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

The same health check still requires the existing non-unit gates: kill switch `CLOSED` from a successful Redis read, an observation result of `PASS` or `OK`, a ledger file present, and no sanitized errors from core units. On the host sidecar, enabled `backend_http` (`/health` on `127.0.0.1:8000`) is also required.

Classes below use the 2026-09-29 Vultr read-only inventory (host `vultr`, no production change). Docker container names are not systemd units. The backend on `127.0.0.1:8000` is covered by the HTTP probe, not by `docker.service`. An allowlisted name that matches nothing here stays `CORE_RUNTIME`.

| Unit | Class | Inventory role |
| --- | --- | --- |
| `nginx.service` | `CORE_RUNTIME` | Enabled TLS edge. The ops site proxies to the Docker backend |
| `project-anchor-commercial-api.service` | `AUXILIARY` | Commercial self-serve API on `127.0.0.1:8010` |
| `project-anchor-payment-webhook.service` | `AUXILIARY` | Payment webhook adapter on `127.0.0.1:8001` |
| `project-anchor-whisper.service` | `AUXILIARY` | Voice server on `127.0.0.1:8088` |
| `project-anchor-word-converter.service` | `AUXILIARY` | Document converter on `127.0.0.1:8791` |
| `project-anchor-kraken-public-shadow-paper-v1-1.service` and `.timer` | `EVALUATION` | Timer-driven shadow paper runtime |
| `project-anchor-evidence-reporter-v1.service` and `.timer` | `AUXILIARY` | Evidence reporter |
| `project-anchor-jev-candidate-review-v1.service` and `.timer` | `EVALUATION` | JEV candidate review shadow |
| `project-anchor-jev-forward-shadow-v1.service` and `.timer` | `EVALUATION` | JEV forward shadow V1 |
| `project-anchor-jev-forward-shadow-v2.service` | `INTENTIONALLY_DISABLED` | Unit file disabled until execute order. Not required for PASS |
| `project-anchor-jev-forward-shadow-v2.timer` | `EVALUATION` | Armed while the service is execute-gated. Not in the default timer list |
| `project-anchor-kraken-forward.service` | `EVALUATION` | Forward collector. Unit file disabled; optional oneshot |
| `project-anchor-kraken-forward.timer` | `EVALUATION` | Still active/waiting, so it is in the default timer list |
| `project-anchor-post-production-monitoring.service` and `.timer` | `AUXILIARY` | Read-only monitoring refresh |
| `project-anchor-kraken-public-shadow-paper-v1-1-monitor.service` | `EVALUATION` | Failed at inventory time. Excluded from the default lists |
| `project-anchor-kraken-turtle-eth-1h-shadow.timer` | `EVALUATION` | Inactive historical timer. Excluded from the default lists |
| `docker.service` | `AUXILIARY` | Not an inventoried systemd control target |

Name rules cover the same roles when the exact unit is not in the table: `whisper`, `word-converter`, `commercial`, and `payment` are `AUXILIARY`. `shadow`, `paper`, `turtle`, `track-b`, `prop-pe`, and `recovery` are `EVALUATION`. `jev-forward-shadow-v2` stays `INTENTIONALLY_DISABLED`.

Journal errors are collected only for `CORE_RUNTIME` services. On this inventory that is `nginx.service`. A disabled, evaluation, or auxiliary unit cannot fail `recent_errors`.

## Recommended allowlists

These match the inventory's production lists. Spaces match the inventory text. Commas are equivalent and are what the example unit uses, because systemd treats an unquoted space as another `Environment=` assignment.

```bash
ANCHOR_CONTROL_MCP_SERVICE_UNITS="nginx.service project-anchor-commercial-api.service project-anchor-payment-webhook.service project-anchor-whisper.service project-anchor-word-converter.service"
ANCHOR_CONTROL_MCP_TIMER_UNITS="project-anchor-post-production-monitoring.timer project-anchor-kraken-public-shadow-paper-v1-1.timer project-anchor-evidence-reporter-v1.timer project-anchor-jev-forward-shadow-v1.timer project-anchor-jev-candidate-review-v1.timer project-anchor-kraken-forward.timer"
```

Of those services, only `nginx.service` gates PASS. The four product services are read and classified `AUXILIARY`. None of the recommended timers gate PASS. `project-anchor-jev-forward-shadow-v2.service` is observed and does not gate PASS. The failed shadow-paper monitor and the inactive turtle timer are classified and left out of the default lists.

Reports directory from the inventory: `/var/lib/project-anchor/reports`.

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

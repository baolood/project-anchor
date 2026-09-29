# ANCHOR_CONTROL_MCP_V1

Read-only MCP control layer for Project Anchor Ops. Grok can query live status through a Custom MCP Connector. The endpoint is fail-closed until an operator sets a credential outside git.

This change does not deploy to Vultr or any other host, does not edit live Nginx, and does not merge itself.

## Endpoint

- App path: `POST /mcp` on the existing FastAPI app (`anchor-backend/app/main.py`)
- Public path, once an operator chooses to route it: `https://<anchor-domain>/mcp`
- Transport: stateless MCP Streamable HTTP (JSON-RPC 2.0). `GET /mcp` returns 405. Notifications return 202.
- Example Nginx route (not applied on a live host): [`nginx/anchor-control-mcp.location.example.conf`](nginx/anchor-control-mcp.location.example.conf)

The backend process already listens on `127.0.0.1:8000` in `anchor-backend/docker-compose.yml`. A future Nginx `location = /mcp` would proxy to `http://127.0.0.1:8000/mcp` and forward the `Authorization` header. Keep raw port 8000 off the public internet.

## Auth

- Env var: `ANCHOR_CONTROL_MCP_TOKEN`
- Client header: `Authorization: Bearer <token>`
- If the env var is unset or empty, `POST /mcp` returns HTTP 503 and serves no tools.
- Query-string credentials are rejected.
- The token is scoped only to the seven tools below. It is separate from `OPS_TOKEN` (that header can change kill-switch state).
- Do not commit a real token. `anchor-backend/.env.example` names the variable and leaves it unset.

Optional: `ANCHOR_CONTROL_MCP_ALLOWED_ORIGINS` (comma-separated exact origins). When unset, a request with an `Origin` header is accepted only when that origin's host matches the request `Host`. Requests with no `Origin` are accepted after the bearer check. Server-side Grok connectors typically omit `Origin`.

Optional unit allowlists, each a comma-separated list of safe unit names (max 8):

- `ANCHOR_CONTROL_MCP_SERVICE_UNITS` (default `project-anchor-post-production-monitoring.service`)
- `ANCHOR_CONTROL_MCP_TIMER_UNITS` (default `project-anchor-post-production-monitoring.timer`)

Optional report directory: `ANCHOR_CONTROL_MCP_REPORTS_DIR`. When unset, the collector reads `<repo>/reports`.

## Stage-1 tools

Exactly these seven, all read-only:

| Tool | What it returns |
| --- | --- |
| `get_anchor_status` | Process up, kill switch enabled/source (`ANCHOR_KILL_SWITCH`, else Redis only when `REDIS_URL` is set, with a short timeout), checklist marker counts, observation/ledger availability |
| `get_latest_observation` | Latest Forward/observation sample (`forward_observation.json`, else the newest allowlisted monitoring report) |
| `get_ledger_summary` | Official Fake-Fill / ledger summary from allowlisted fake-fill report JSON |
| `get_services` | `systemctl show` for the service allowlist |
| `get_timers` | `systemctl show` for the timer allowlist |
| `get_recent_errors` | Sanitized journal errors for the service allowlist, plus sanitized artifact error strings |
| `run_readonly_healthcheck` | One combined read-only health check over the other views |

`tools/list` advertises only this set. Any other tool name, including shell, SSH, file read, or order placement, is rejected.

## Hard boundaries

The MCP surface must not:

- read or return `.env` files, API keys, Kraken keys, database passwords, bearer tokens, or DSNs
- access accounts, place orders, trade, or withdraw
- write to the database or change governance
- start, stop, restart, or reload services
- expose SSH or an arbitrary shell
- deploy, change live Nginx, or merge this branch by itself

systemd access is a fixed argv allowlist (`systemctl show` and `journalctl -u <service> -p err`). Report JSON is read only from an allowlisted basename inside the reports directory. Symlinks that resolve outside that directory are ignored. Payloads are projected to status fields and then redacted.

Live trading and go-live remain `NO-GO` in every tool envelope.

## Connect Grok Custom MCP

1. Set `ANCHOR_CONTROL_MCP_TOKEN` in the backend process environment on the host that will serve `/mcp`. Leave it unset until that host is intentionally configured. This repository change does not do that configuration.
2. Route `https://<anchor-domain>/mcp` to the FastAPI path using the example Nginx snippet, on a host change that is reviewed separately.
3. In Grok, add a Custom MCP Connector:
   - Server URL: `https://<anchor-domain>/mcp`
   - Transport: Streamable HTTP
   - Header: `Authorization: Bearer <same value as ANCHOR_CONTROL_MCP_TOKEN>`
4. Store the token in the connector secret store. Do not paste it into git, docs, or chat logs.
5. Confirm `tools/list` returns the seven tools above and nothing else.
6. A 503 response means the env var is still unset (fail closed). A 401 means the bearer token does not match.

## Local check

```bash
cd /path/to/project-anchor
PYTHONPATH=anchor-backend python3 -m unittest discover -s anchor-backend/tests -p test_anchor_control_mcp_v1.py
```

## Non-goals

- Production deploy, Vultr changes, live Nginx edits, firewall or DNS changes
- Auto-merge
- Trading, order, withdrawal, or account tools
- Write tools, service control, SSH, or a general shell
- Reading secrets or credential files

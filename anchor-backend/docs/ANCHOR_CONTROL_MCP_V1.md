# ANCHOR_CONTROL_MCP_V1

Read-only MCP control layer for Project Anchor Ops. Grok can query live status through a Custom MCP Connector. The endpoint is fail-closed until an operator sets a credential outside git.

This change does not deploy to Vultr or any other host, does not edit live Nginx, and does not merge itself.

## Endpoint

- App path: `POST /mcp` on the existing FastAPI app (`anchor-backend/app/main.py`)
- Public path, once an operator chooses to route it: `https://<anchor-domain>/mcp`
- Transport: stateless MCP Streamable HTTP (JSON-RPC 2.0). `GET /mcp` returns 405. Notifications return 202.
- Example Nginx route (not applied on a live host): [`nginx/anchor-control-mcp.location.example.conf`](nginx/anchor-control-mcp.location.example.conf)

The backend process already listens on `127.0.0.1:8000` in `anchor-backend/docker-compose.yml`. That container cannot reliably see host systemd, so the public MCP path must not stop at the container. The host sidecar in [`ANCHOR_CONTROL_MCP_HOST_SIDECAR_V1.md`](ANCHOR_CONTROL_MCP_HOST_SIDECAR_V1.md) listens on `127.0.0.1:8021` and is the process that may call `systemctl show`. `127.0.0.1:8001` is already the payment webhook on the inventoried host. The example Nginx `location = /mcp` proxies to `http://127.0.0.1:8021/mcp` and forwards the `Authorization` header. Keep raw ports 8000 and 8021 off the public internet. The Docker publish line stays `127.0.0.1:8000:8000`.

## Auth

- Env var: `ANCHOR_CONTROL_MCP_TOKEN`
- Client header: `Authorization: Bearer <token>`
- If the env var is unset or empty, `POST /mcp` returns HTTP 503 and serves no tools.
- Query-string credentials are rejected.
- The token is scoped only to the tools below. It is separate from `OPS_TOKEN` (that header can change kill-switch state).
- Do not commit a real token. `anchor-backend/.env.example` names the variable and leaves it unset.

Optional: `ANCHOR_CONTROL_MCP_ALLOWED_ORIGINS` (comma-separated exact origins). When unset, a request with an `Origin` header is accepted only when that origin's host matches the request `Host`. Requests with no `Origin` are accepted after the bearer check. Server-side Grok connectors typically omit `Origin`.

Deploy-time unit allowlists, each a comma-separated or whitespace-separated list of safe unit names (max 8):

- `ANCHOR_CONTROL_MCP_SERVICE_UNITS`
- `ANCHOR_CONTROL_MCP_TIMER_UNITS`

Set both to the real Anchor service and timer units installed on that host before relying on `get_anchor_status` or `run_readonly_healthcheck`. Inside the Docker backend the built-in default is only `project-anchor-post-production-monitoring.service` and `project-anchor-post-production-monitoring.timer`. That pair is the read-only monitoring refresh. It is not the full runtime picture (backend, worker, and any other units the operator actually runs). The host sidecar class table started from the 2026-09-29 read-only Vultr inventory. Its timer allowlist matches the 2026-10-23 founder list: post-production monitoring, Kraken forward, JEV forward shadow v2, the official ledger, and the read-only ledger mirror. See [`ANCHOR_CONTROL_MCP_HOST_SIDECAR_V1.md`](ANCHOR_CONTROL_MCP_HOST_SIDECAR_V1.md). Only `CORE_RUNTIME` gates PASS. On that inventory the core service is `nginx.service`. `project-anchor-jev-forward-shadow-v2.service` is `INTENTIONALLY_DISABLED` and is not required to be active. Its timer is `EVALUATION` and stays on the timer allowlist. Commercial, payment, whisper, and word-converter stay `AUXILIARY`. Process health is derived only from `systemctl show` of the configured service units. Long-running services pass only when `ActiveState=active`. `inactive` or `dead` with `Result=success` is a stopped service and is `FAILED`, not healthy. A oneshot unit is idle-healthy only when `systemctl show` reports `Type=oneshot` and `Result=success`. Other service types do not get that exception. If the read is missing, process state is `UNKNOWN`. `UNKNOWN` and `FAILED` are not reported as `PASS`. Timers pass only when `ActiveState=active`. On the host sidecar that per-unit flag gates the timer check only for `CORE_RUNTIME`. The 2026-10-23 allowlist has no `CORE_RUNTIME` timers, so an idle ledger or evaluation timer does not fail PASS.

Optional report directory: `ANCHOR_CONTROL_MCP_REPORTS_DIR`. When unset, the collector reads `<repo>/reports`.

Optional Official V2 ledger directory: `ANCHOR_CONTROL_MCP_LEDGER_DIR`. When unset, `get_ledger_summary` keeps reading allowlisted fake-fill report JSON inside the reports directory. When set, the resolved path must be exactly `/var/lib/anchor-ledger-mirror`. The ledger StateDirectory (`/var/lib/anchor-official-ledger-20261010` and `/var/lib/private/anchor-official-ledger-20261010`) is not allowlisted. Any other path, including a child directory, a relative path, or a sensitive path, is rejected and the tool does not fall back to report JSON. The reader lists regular files directly in that mirror directory named `anchor_fake_fill_ledger_v2_official*.jsonl` or `.csv`. It does not recurse and it does not open the StateDirectory. It opens with read-only flags and skips symlinks. Before summarizing, it verifies the sibling `.sha256` sidecar. A missing sidecar, a symlink, a bad line, or a digest mismatch makes the summary unavailable and omits the hash-chain head. `mirror_stale` is true when `copied_at` in the `.meta.json` sidecar is missing or older than 90 minutes (`mirror_age_sec` greater than 5400). A hash match stays `available: true` when the mirror is stale. The summary includes event counts, last event id, last event time, hash-chain head, and `realized_pnl_cum`, plus `mirror_copied_at`, `mirror_age_sec`, `mirror_stale`, `mirror_stale_after_sec`, `mirror_source_mtime`, `mirror_source_size`, and `mirror_sha256_ok`. Live rows name the id `ledger_event_id` and the hash `row_hash`. Last event time is the latest parseable value on the last row among `signal_available_at`, `fill_time_utc`, `signal_candle_open_utc`, and `event_time`. `last_event_time_field` names which of those fields supplied it. Equal timestamps prefer that same order. A missing offset is treated as UTC. A historical CSV whose header column count differs from a data row is parsed from that row's own columns. Per-exit `NET_PNL` rows exclude entry costs. `realized_pnl_cum` is the ledger cumulative figure, not an exchange cash balance. The copy from the StateDirectory is `anchor-ledger-readonly-mirror.service`, described in [`ANCHOR_LEDGER_READONLY_MIRROR_V1.md`](ANCHOR_LEDGER_READONLY_MIRROR_V1.md).

Optional C6 series directory: `ANCHOR_CONTROL_MCP_C6_SERIES_DIR`. When unset, `get_ledger_summary` still returns a `c6_series` object with `available: false` and does not open a default path. When set, the directory must be absolute and must not be a symlink. Line A paths are rejected unread: a path component containing `affl-v2-official-ledger` or `anchor-official-ledger` (other than the exact names `affl-v2-official-ledger-c6` and `anchor-official-ledger-c6`), `/var/lib/private`, the Official StateDirectory, or the read-only mirror. The reader opens only `out/anchor_fake_fill_equity_v2_1_official.csv` read-only, without following links. `c6_series` is `available`, `rows`, `last_row_time`, `position_state`, `scoring_status`, and `read_only`. It does not include mark prices, funding rates, or row bodies. That keeps the block small; the connector truncates near 2.6 KB. The host drop-in template is `docs/templates/anchor-control-mcp.service.d/30-c6-series.conf`. This repository change does not install it.

## Stage-1 tools

Exactly these tools, all read-only:

| Tool | What it returns |
| --- | --- |
| `get_anchor_status` | Process state from allowlisted `systemctl show` (long-running services `PASS` only when `ActiveState=active`; stopped `Result=success` is `FAILED`; `Type=oneshot` may be idle-healthy; otherwise `UNKNOWN` or `FAILED`), kill switch (`OPEN` when `ANCHOR_KILL_SWITCH=1` or Redis reads on; `CLOSED` only after a successful Redis read of off; `UNKNOWN` when Redis cannot be read), checklist marker counts, observation/ledger availability |
| `get_latest_observation` | Latest Forward/observation sample (`forward_observation.json`, else the newest allowlisted monitoring report). Repo-recorded order checks are renamed away from exchange-confirmation labels. `exchange_confirmed_order_status` is `UNKNOWN` unless that snapshot records an offline reconciliation file; it is never inferred from a repo-recorded PASS. A monitoring artifact whose result would otherwise be plain `PASS` without that file is projected as `PASS_REPO_RECORDED_ONLY`. That label does not degrade `run_readonly_healthcheck` |
| `get_ledger_summary` | Official Fake-Fill summary. With `ANCHOR_CONTROL_MCP_LEDGER_DIR` unset, allowlisted fake-fill report JSON. With that env var set, Official V2 counts from `/var/lib/anchor-ledger-mirror` only, after the `.sha256` sidecar matches. Last event id (`ledger_event_id`), last event time (latest of `signal_available_at`, `fill_time_utc`, `signal_candle_open_utc`, or `event_time`, with `last_event_time_field` naming the source), hash-chain head (`row_hash`), and `realized_pnl_cum`. `mirror_stale` is set when `copied_at` is older than 90 minutes. Per-exit `NET_PNL` rows exclude entry costs. `c6_series` is the compact C6 block from `ANCHOR_CONTROL_MCP_C6_SERIES_DIR` when that variable is set |
| `get_services` | `systemctl show` for the service allowlist |
| `get_timers` | `systemctl show` for the timer allowlist |
| `get_recent_errors` | Sanitized journal errors for the service allowlist, plus sanitized artifact error strings |
| `run_readonly_healthcheck` | One combined read-only health check over the other views |
| `get_mf4_status` | MF4 watcher `status.json` when `ANCHOR_CONTROL_MCP_MF4_DIR` is set. Read-only, no network. Unset or rejected paths return `available: false` |
| `get_eval_state` | Manual Kraken Prop snapshot plus the eval guard. `source` is `manual-snapshot`. A snapshot older than 24 hours is `guard_verdict` `unknown`. `account_status` `locked` is distinct from `breached`. `pass_probability` is a fixed-seed Monte Carlo. No exchange API |

`tools/list` advertises only this set. Any other tool name, including shell, SSH, file read, or order placement, is rejected. `get_mf4_status` and `get_eval_state` stay in the registry and do nothing until `ANCHOR_CONTROL_MCP_MF4_DIR` is set outside git. See [`docs/ANCHOR_MF4_EVAL_TOOLS_V1.md`](../../docs/ANCHOR_MF4_EVAL_TOOLS_V1.md).

## Hard boundaries

The MCP surface must not:

- read or return `.env` files, API keys, Kraken keys, database passwords, bearer tokens, or DSNs
- access accounts, place orders, trade, or withdraw
- write to the database or change governance
- start, stop, restart, or reload services
- expose SSH or an arbitrary shell
- deploy, change live Nginx, or merge this branch by itself

systemd access is a fixed argv allowlist (`systemctl show` and `journalctl -u <service> -p err`). Report JSON is read only from an allowlisted basename inside the reports directory. Symlinks that resolve outside that directory are ignored. The Official V2 ledger is read only when `ANCHOR_CONTROL_MCP_LEDGER_DIR` names `/var/lib/anchor-ledger-mirror`, and only through read-only opens after the `.sha256` sidecar matches. The MCP does not read the ledger StateDirectory. Payloads are projected to status fields and then redacted.

Live trading and go-live remain `NO-GO` in every tool envelope.

Kill-switch reads fail closed. An unread or failed Redis read is `UNKNOWN` and the combined health check is not `PASS`. It is not treated as closed or normal. A confirmed off state requires a successful Redis read. `ANCHOR_KILL_SWITCH=1` is `OPEN`.

## Connect Grok Custom MCP

1. Set `ANCHOR_CONTROL_MCP_TOKEN` in the backend process environment on the host that will serve `/mcp`. Leave it unset until that host is intentionally configured. This repository change does not do that configuration.
2. Route `https://<anchor-domain>/mcp` to the FastAPI path using the example Nginx snippet, on a host change that is reviewed separately.
3. In Grok, add a Custom MCP Connector:
   - Server URL: `https://<anchor-domain>/mcp`
   - Transport: Streamable HTTP
   - Header: `Authorization: Bearer <same value as ANCHOR_CONTROL_MCP_TOKEN>`
4. Store the token in the connector secret store. Do not paste it into git, docs, or chat logs.
5. Confirm `tools/list` returns the tools above and nothing else.
6. A 503 response means the env var is still unset (fail closed). A 401 means the bearer token does not match.

## Local check

```bash
cd /path/to/project-anchor
PYTHONPATH=anchor-backend python3 -m unittest discover -s anchor-backend/tests -p 'test_anchor_control_mcp*.py'
```

## Non-goals

- Production deploy, Vultr changes, live Nginx edits, firewall or DNS changes
- Auto-merge
- Trading, order, withdrawal, or account tools
- Write tools, service control, SSH, or a general shell
- Reading secrets or credential files

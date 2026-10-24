# ANCHOR MF4 EVAL TOOLS V1

DEPLOY=NO. Nothing in this change is installed, and nothing here places an order.

Kraken Prop has no API (vendor FAQ); eval state is a manual snapshot; orders remain manual in browser.

The vendor FAQ on kraken.com/pro/prop says Kraken Prop does not currently offer API access for evaluation or funded accounts, and that orders are placed manually in the trading interface. A key on the normal Kraken account would not see the eval wallet. This repository does not add a private Kraken client, an order call, or a place to store an exchange key.

## What was added

| Path | Role |
| --- | --- |
| `ops/mf4/_b1_core.py` | Public 4h breakout, 4R target. No I/O |
| `ops/mf4/mf4_host_watcher.py` | Public `PF_XBTUSD` ticker and 4h candles, writes `status.json` |
| `ops/mf4/mf4_webhook.py` | Signal webhook. `MF4_WEBHOOK_ENABLED` defaults to `0` |
| `ops/mf4/eval_guard.py` | Daily line, floor, worst case at the stop |
| `ops/mf4/mf4_record_actual.py` | `--account` writes `eval_account.json` mode `0640` |
| `ops/mf4/anchor-mf4-watcher.service` | Unit template. Not installed |
| `ops/mf4/anchor-mf4-watcher.service.diff` | Webhook lines for that unit |
| `ops/mf4/ROLLBACK_MF4_WATCHER.sh` | Stops the unit. Does not print or delete the webhook file |
| `anchor-backend/app/mcp/mf4_eval.py` | `get_mf4_status` and `get_eval_state` |

`anchor-mf4-watcher.service` is `EVALUATION` in the MCP inventory. It is not on the default allowlist and it does not gate PASS.

`ops/mf4/` was absent on main when this change was written. The signal core is isolated in `_b1_core.py`. The host sha256 recorded for that file (`f2834232…ae52`) was not in this checkout, so this copy is not a byte-for-byte claim against the host. The webhook, guard, and MCP readers call `decide` and do not inline its arithmetic.

## Webhook

Standing delivery requires `MF4_WEBHOOK_ENABLED=1`. The default is `0`. The watcher loop does not post while the flag is off.

The credential file is operator-owned, outside git:

- `/etc/anchor-mf4-watcher/webhook.env` (`root:anchor-mf4`, mode `0640`), or
- systemd `LoadCredential=webhook:/etc/anchor-mf4-watcher/webhook.env`, which the unit sees as `$CREDENTIALS_DIRECTORY/webhook` mode `0400`

`MF4_WEBHOOK_ENV_FILE` is the other accepted path, for a local test. Keys:

| Key | Default |
| --- | --- |
| `EVAL_WEBHOOK_URL` | required |
| `EVAL_WEBHOOK_KEY` | required |
| `EVAL_WEBHOOK_KEY_HEADER` | `Authorization` |
| `EVAL_WEBHOOK_KEY_FORMAT` | `Bearer {key}` |

Payload on an OPEN or an EXIT:

```json
{"signal":"OPEN","strategy":"MF4_BRK4H_4R","price":0,"time_shanghai":"","reason":"","test":false,"source":"anchor-host","event_id":"","guard":{}}
```

`event_id` is remembered in `$MF4_OUT_DIR/webhook_state.json`. A second process with the same directory does not post that id again. A failed post is appended to `webhook_outbox.jsonl` and retried on the next watcher step, with three retries spaced 2s, 5s, and 15s. The HTTP timeout is 15s. The post runs on a daemon thread so a network error cannot stall candle handling and cannot crash the watcher. The URL and the key are redacted before any log line, and they are not written into `status.json`.

`--send-test` posts one payload with `test: true`. It does not flip `MF4_WEBHOOK_ENABLED`.

## Guard

Inputs are `eval_account.json` (`balance`, `daily_ref_balance`, `daily_ref_at`, `floor`, `target`, `position`, `snapshot_at`) and the public PF mark.

- `daily_line` = 97% of `daily_ref_balance`, rounded half-up to cents. 08:30 Asia/Shanghai is 00:30 UTC.
- `floor` defaults to 9,400. `target` defaults to 11,000.
- `est_equity` = balance + size × (mark − entry), signed by side, minus 0.05% fees per side at the entry and the mark.
- `worst_case_at_sl` = the stop move, minus 0.05% fees per side on entry and stop, minus 0.1% slippage on the stop.
- `max_size_for_signal` = min(`MF4_RISK_USD` when set, 50% of `headroom_daily`) / stop distance.
- `block` when estimated equity or worst-case equity is through the daily line or the floor.
- `warn` when a headroom is under half of that line's budget (3% of the daily reference, or the reference minus the floor).
- `unknown` when the snapshot is missing or older than 24 hours, when `daily_ref_at` is before the latest 00:30 UTC, or when an open position has no mark. `unknown` is never reported as `ok`.

2026-10-22 recorded trade, used as the fixture: balance 10,120.42, daily reference 10,120.42, so the daily line is 9,816.81. Long 0.176 BTC, entry 84,499.5, stop 83,633.1. The stop move is about −152.5, fees about 14.8, slippage about 14.7, and the worst case rounds to −182. With the mark at the entry, that worst case stays above both lines, so the verdict is `ok`.

The watcher writes that guard object into `status.json` and into the webhook body. `mf4_record_actual.py --account snapshot.json --out-dir <dir>` is how the operator stores the page reading. The script refuses Line A and sealed paths and does not open them.

## MCP

Both tools are read-only. They do not open a socket. They read at most the last 64 KB of a regular file, they do not follow symlinks, and they reject Line A, `/var/lib/private`, and sensitive paths via the existing sealed-path and `looks_sensitive_path` checks. Responses go through `sanitize.py`. Each tool envelope is capped at 2.5 KB.

Set `ANCHOR_CONTROL_MCP_MF4_DIR` to an absolute directory that is not a Line A path. When it is unset, both tools return `available: false`.

`get_mf4_status` returns `state`, `pos`, `trend`, `long_trigger_gt`, `short_trigger_lt`, `last_4h_close` (`at_sh`, `close`), `last_signal` (`type`, `side`, `price`, `at_sh`), `price` (`last`, `age_s`, `fresh` when the tick is under 120 seconds), `shadow_equity`, `webhook` (`enabled`, `last_ok_at_sh`, `outbox_n`), `compare` (`consecutive_matches`, `last_diff_at`), and `reason`.

`get_eval_state` returns `balance`, `est_equity`, `daily_line`, `floor`, `target`, `headroom_daily`, `headroom_floor`, `position`, `snapshot_age_s`, `guard_verdict`, and `source` = `manual-snapshot`.

## Unit and rollback

`ops/mf4/anchor-mf4-watcher.service` is a template. It sets `Environment=MF4_WEBHOOK_ENABLED=0`, `LoadCredential=webhook:/etc/anchor-mf4-watcher/webhook.env`, and `ReadOnlyPaths` including `/etc/anchor-mf4-watcher`. `RestrictAddressFamilies` stays `AF_INET` and `AF_INET6`. The unit is not enabled by this change.

`ops/mf4/ROLLBACK_MF4_WATCHER.sh` disables that unit and deletes the unit file under `/etc/systemd/system`. It leaves `/var/lib/anchor-mf4-watcher` in place. It does not read or delete the webhook env file. It does not touch Line A, the sealed ledger, the legacy equity CSV, the governance register, or the PASS LINE freeze record.

## Out of scope

Line A, the sealed StateDirectory, the legacy equity CSV, `governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl`, and `docs/PROJECT_ANCHOR_PASS_LINE_V1_1_FREEZE_RECORD.md` are not modified. The box watcher is not stopped. Browser orders stay manual.

## Verify

```bash
cd /path/to/project-anchor
export PYTHONPATH=.
python3 -m unittest tests.test_mf4_eval_tools
PYTHONPATH=anchor-backend python3 -m unittest anchor-backend.tests.test_anchor_control_mcp_mf4_eval
```

The second command needs the parent on `PYTHONPATH` as well when the test imports `ops.mf4`. From the repo root:

```bash
PYTHONPATH=.:anchor-backend python3 -m unittest tests.test_mf4_eval_tools anchor-backend.tests.test_anchor_control_mcp_mf4_eval
```

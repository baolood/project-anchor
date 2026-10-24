# ANCHOR MF4 EVAL TOOLS V1

DEPLOY=NO. Nothing in this change is installed, and nothing here places an order.

Kraken Prop has no API (vendor FAQ); eval state is a manual snapshot; orders remain manual in browser.

The vendor FAQ on kraken.com/pro/prop says Kraken Prop does not currently offer API access for evaluation or funded accounts, and that orders are placed manually in the trading interface. A key on the normal Kraken account would not see the eval wallet. This repository does not add a private Kraken client, an order call, or a place to store an exchange key.

## What was added

| Path | Role |
| --- | --- |
| `ops/mf4/_b1_core.py` | Live MF4 core, byte-for-byte. Public PF_XBTUSD futures charts |
| `ops/mf4/mf4_host_watcher.py` | Host stepper for those charts. Webhook default off. Writes `status.json` |
| `ops/mf4/verify_chain.py` | Read-only check of the forward-stream hash chain |
| `ops/mf4/mf4_webhook.py` | Signal webhook. `MF4_WEBHOOK_ENABLED` defaults to `0` |
| `ops/mf4/eval_guard.py` | Daily line, floor, worst case, cap-150 size |
| `ops/mf4/pass_prob.py` | Fixed-seed pass / breach / locked Monte Carlo |
| `ops/mf4/eval_outcomes.py` | Append-only manual trade log and cost summary |
| `ops/mf4/mf4_record_actual.py` | `--account` writes `eval_account.json` mode `0640` |
| `research/` | Locked eval studies, research gate, random-direction control |
| `ops/mf4/anchor-mf4-watcher.service` | Unit template. Not installed |
| `ops/mf4/anchor-mf4-watcher.service.diff` | Webhook lines for that unit |
| `ops/mf4/ROLLBACK_MF4_WATCHER.sh` | Stops the unit. Does not print or delete the webhook file |
| `anchor-backend/app/mcp/mf4_eval.py` | `get_mf4_status` and `get_eval_state` |

`anchor-mf4-watcher.service` is `EVALUATION` in the MCP inventory. It is not on the default allowlist and it does not gate PASS.

`ops/mf4/_b1_core.py` is the live MF4 core, byte-for-byte. Its sha256 is `f2834232bccf10d546e0ef769753042cc0becda86f09ca0960c3cb1ff818ae52`. The rule is 4h Donchian20 plus a daily EMA50 filter on Kraken Futures `PF_XBTUSD`, stop `max(1.0×ATR4h, 0.35% of entry)`, target 4R, size from `MF4_RISK_USD` (default 150), one virtual position, stop-first on 15m bars. Entry reference is the 4h close. The watcher calls that core. It does not inline the arithmetic.

The watcher is the host stepper, including the restart fix: `state.json` stores numbers as text, and those strings load back as floats so an open position still exits after a restart. `status.json` keeps the host compare fields (`last_4h_close_sh`, trend, triggers) and adds the fields `get_mf4_status` reads: `price` (`last`, `at`), `last_4h_close` (`at_sh`, `close`), `last_signal` (`type`, `side`, `price`, `at_sh`), and `compare`. Webhook delivery and the eval guard sit on that stepper. Both stay quiet unless the operator turns the webhook flag on or writes `eval_account.json`.

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
- `block` when estimated equity or worst-case equity is through the daily line or the floor (`worst_case_breaches_line`).
- `block` with reason `too_close` when planned risk is under $50. That skip is logged as `eval_guard skip reason=<reason> planned_risk=<dollars>`.
- `warn` when a headroom is under half of that line's budget (3% of the daily reference, or the reference minus the floor).
- `unknown` when the snapshot is missing or older than 24 hours, when `daily_ref_at` is before the latest 00:30 UTC, or when an open position has no mark. `unknown` is never reported as `ok`, and it is logged as a skip.

Planned risk (decision 2026-10-24), returned as `planned_risk`:

```text
min(150, equity - daily_line - 30, equity - 9400 - 30)
```

`9400` is the account floor (the snapshot floor when one is set). If the trade may still be open at the next 00:30 UTC, also cap at `0.03 * balance - 30`. That flag defaults off on `evaluate`; the watcher sets it for an OPEN signal or an open position, and `get_eval_state` sets it because an MF4 hold can cross the reset. Size is `planned_risk / (|entry - stop| + 2 * 0.0004 * entry)`, floored to 0.001 BTC. The 0.04% figure is the prop commission. The worst-case cushion above stays 0.05% plus 0.1% slippage.

2026-10-22 recorded trade, used as the fixture: balance 10,120.42, daily reference 10,120.42, so the daily line is 9,816.81. Long 0.176 BTC, entry 84,499.5, stop 83,633.1. The stop move is about −152.5, fees about 14.8, slippage about 14.7, and the worst case rounds to −182. With the mark at the entry, that worst case stays above both lines, so the verdict is `ok`.

The watcher writes that guard object into `status.json` and into the webhook body. `mf4_record_actual.py --account snapshot.json --out-dir <dir>` is how the operator stores the page reading. The script refuses Line A and sealed paths and does not open them.

## MCP

Both tools are read-only. They do not open a socket. They read at most the last 64 KB of a regular file, they do not follow symlinks, and they reject Line A, `/var/lib/private`, and sensitive paths via the existing sealed-path and `looks_sensitive_path` checks. Responses go through `sanitize.py`. Each tool envelope is capped at 2.5 KB.

Set `ANCHOR_CONTROL_MCP_MF4_DIR` to an absolute directory that is not a Line A path. When it is unset, both tools return `available: false`.

`get_mf4_status` returns `state`, `pos`, `trend`, `long_trigger_gt`, `short_trigger_lt`, `last_4h_close` (`at_sh`, `close`), `last_signal` (`type`, `side`, `price`, `at_sh`), `price` (`last`, `age_s`, `fresh` when the tick is under 120 seconds), `shadow_equity`, `webhook` (`enabled`, `last_ok_at_sh`, `outbox_n`), `compare` (`consecutive_matches`, `last_diff_at`), and `reason`.

`get_eval_state` returns `balance`, `est_equity`, `daily_line`, `floor`, `target`, `headroom_daily`, `headroom_floor`, `planned_risk`, `size`, `account_status`, `position`, `snapshot_age_s`, `guard_verdict`, `pass_probability`, and `source` = `manual-snapshot`.

`account_status` is `running`, `passed` (equity at the target), `locked`, or `breached`. `locked` means equity is still above the floor and the daily line, but equity − floor − 30 is under $50, so the account can no longer open a trade at the minimum risk. `breached` means equity is already through the floor or the daily line. A stale snapshot stays `unknown`.

`pass_probability` is a fixed-seed (7) Monte Carlo of 20,000 paths, ported from `research/eval-pass-prob/lib.py`. It uses estimated equity, the last-reset balance, floor 9,400, target 11,000, and the cap-150 rule. Trade outcomes come from `eval_trades.jsonl` in the MF4 directory (last 64 KB). Until that file has at least 20 usable trades, the book stays the zero-edge 4R baseline (costs 0.09R per trade), so one losing trade does not show a 0% pass. At 20 trades the stored book is the book. The block reports pass, breach, locked, and running at 30, 60, and 90 days and at a 1,095-day no-limit horizon, plus median days to resolve. It finishes in under a second. The whole tool reply stays within 2.5 KB.

## Trade log

`ops/mf4/eval_outcomes.py` appends one operator-typed trade to `eval_trades.jsonl` (mode `0640`). Kraken Prop has no API, so this is manual. Fields: signal id, side, entry, stop, tp, size, realized R, commission, funding, MAE, MFE, duration, exit reason. `--summary` prints fees and funding in R (sum and mean) and does not append. The writer refuses Line A, the sealed ledger, the legacy equity CSV, the governance register, and the PASS LINE freeze record, and it does not open them.

## Research record

`research/RESEARCH_GATE.md` (including §8), `research/eval-pass-prob/`, `research/eval-dir-families/`, and `research/PASS_PROB_20261024.md` are the 2026-10-24 study. `PARAMS.lock` hashes are unchanged. `research/random_direction.py` is the reusable P3 control (`Rnd`, `match_p`). It does not place orders.

## Unit and rollback

`ops/mf4/anchor-mf4-watcher.service` is a template. It sets `Environment=MF4_RISK_USD=150`, `Environment=MF4_WEBHOOK_ENABLED=0`, `LoadCredential=webhook:/etc/anchor-mf4-watcher/webhook.env`, and `ReadOnlyPaths` including `/etc/anchor-mf4-watcher`. `RestrictAddressFamilies` stays `AF_INET` and `AF_INET6`. The unit is not enabled by this change. A 90-day PF_XBTUSD replay of this stepper (2026-07-26 12:00 through 2026-10-24 13:15 Asia/Shanghai) is 13 trades and 26 signals, the same times and prices as the live host.

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
PYTHONPATH=.:anchor-backend python3 -m unittest tests.test_mf4_eval_tools tests.test_eval_pass_prob tests.test_research_random_direction anchor-backend.tests.test_anchor_control_mcp_mf4_eval
```

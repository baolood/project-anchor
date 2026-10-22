# Official Fake-Fill Line A scoring-field gap

**Document ID:** `ANCHOR_OFFICIAL_FAKE_FILL_LINE_A_SCORING_FIELD_GAP_V1`  
**Status:** inventory for the V1.1 pass-line draft. Not a grade.  
**Pass line:** `docs/PROJECT_ANCHOR_OFFICIAL_EVALUATION_PASS_LINE_V1_1_FINAL_DRAFT.md`  
**Scorer:** `scripts/score_official_fake_fill_pass_line.py`  
**Line A source of key names:** 2026-09-30 read-only preflight of `anchor_fake_fill_ledger_v2_official.jsonl` (41 top-level keys; flat objects; no nested trade struct). The preflight covered about 150 events. The file later grew. This inventory was not re-dumped from the 1666-row mirror, because that summary API does not return row keys. The scorer trusts the keys on the copy it reads.

**Derivable** means the value follows from fields on the same row or the paired row by arithmetic the pass line states. A proxy with a different name is not derivable. A missing amount is `MISSING`, not `0`.

## Gap table

| Required field | Present on Line A? | Derivable? | Source | Action |
|----------------|--------------------|------------|--------|--------|
| `fee_paid`, `fee_bps` | Yes, key on events | Yes, recorded amount | JSONL fill rows | **Line A.** Subtract the recorded amount. A missing key or null is `MISSING`, not zero. A recorded `0` is a real zero. |
| `slippage_cost`, `slippage_bps` | Yes | Yes, recorded amount | JSONL fill rows | **Line A.** Same rule as fees. |
| Entry costs inside the exit net | Exit key `NET_PNL_EX_FUNDING` is present | Yes, by subtraction | Exit `NET_PNL_EX_FUNDING` (or `net_pnl` when it is the same number), minus entry `fee_paid` and entry `slippage_cost` | **Line A.** Per-exit net excludes entry costs. `realized_pnl_cum` is not the trade net. If both net names exist and differ, the trade is inconsistent and is not averaged. |
| `gross_pnl` | Yes | Cross-check | Exit row | **Line A.** When gross and all four fee/slip amounts exist, recompute the round trip. Disagreement is `NET_AND_GROSS_INCONSISTENT`. |
| `funding_pnl` | Key yes, value null in the preflight | No | `FUNDING_DATA_STATUS=MISSING`, `NET_PNL_STATUS=EX_FUNDING` | **Line A.** Leave `MISSING`. Do not zero-fill. `PRESENT` plus amount `0` is the only real zero. `PARTIAL` is not summed. C3, C4, C8, and official R0 stay `NOT_SCORABLE` until `PRESENT`. |
| `fill_time_utc` | Yes on `OPEN`, `REVERSE_ENTRY`, `FLAT_EXIT`, `REVERSE_EXIT`; null on other types | Yes, as the fill clock | Those four event types | **Line A.** Entry and exit times. Other event types are not fills. |
| `signal_available_at` | Yes | Yes, as the signal clock | All preflight event types | **Line A.** T0 signal filter when the key exists. Latency diagnostic. Not a fill price. |
| `signal_candle_open_utc` | Yes | Not a fill | All preflight event types | **Line A.** Retained. Not used as fill time or fill price. |
| `effective_price` | Yes (key in the 41) | Yes, as the fill price when the row is a fill | Fill rows | **Line A.** R0 price path. |
| `signal_price`, `reference_price` | Yes | No as a fill | Fill and signal rows | **Line A.** Not substituted for `effective_price`. They are prices from before the fill, or a reference the fill rule already consumed. |
| `side`, `quantity` | Yes | Yes | Entry row | **Line A.** Pairing and R0. Quantity is copied, not resized. |
| `notional`, `fill_notional` | Yes | Not as risk and not as a new size | Entry row | **Line A.** Historical size. A later capital-allocation rule needs its own T_alloc on Line B. |
| `trade_id` | No | No as a stored id | File order plus `ledger_event_id` | **Line A.** Pair in append order. Do not write `trade_id` back onto old rows. **Line B** may store `tr_` + entry id on new rows only. |
| `preset_stop_price` (also any `stop_price` / `stop_loss`) | No | No | Absent from JSONL and from `LedgerEvent` in the preflight | **Line B.** Do not back-calculate a stop from later prices or from realized loss. |
| `equity_at_open` | No literal | No | `OPEN.net_liquidation_equity` is a different field | **Line B.** Do not alias the equity column. The readiness note's proxy is refused. |
| `risk_amount`, `risk_pct` | No | No | Would need a preset stop and equity at open, both absent | **Line B.** Do not infer risk from notional, from `10000` starting equity, or from outcome PnL. |
| `net_liquidation_equity` | Yes | Yes, as curve points for C5 only | JSONL events | **Line A.** C5 recomputes peak-to-trough on `[T0, T_score]`. Fills use `fill_time_utc`. Other rows use `signal_available_at`. |
| Stored `drawdown` | Yes | No for the post-T0 maximum | Row value can include a pre-T0 peak | **Line A.** Ignore the stored column. Recompute C5. |
| CST `day_open` / `day_low` | No | No | `MARK_RULE_C7_V1` marks are not on Line A | **Line B / equity v2.1.** C7 stays `NOT_SCORABLE`. `FLAT_MARK` is not an intraday low. An `OHLC_ADVERSE_PROXY` labeled `NOT_TICK_LOW` is not the day low. |
| Governance incident counts | No | No | Not on the trade ledger | **Separate register.** Absence is not `0`. C9 needs `ATTEST_COVERAGE` over `[T0, T_score]` plus any `INCIDENT` rows. PR #416 lists future paths and does not create the register. |
| `prev_hash`, `row_hash` | Yes | Linkage only | JSONL | **Line A.** Structural chain is checked. A break FAILs. Payload recomputation is `NOT_SCORABLE` until the writer canonicalization is in this repository. |
| `ledger_event_id` | Yes | Identity of the row, not of the trade | JSONL | **Line A.** Unique, and `le-N` must step by 1. A gap FAILs C10. The id is not rewritten to hide a missing row. |
| `realized_pnl_cum` | Yes | No as C3 | Last-row cumulative | **Line A.** Includes the pre-T0 book and is not the paired post-T0 official net. |
| `observation_id`, `source_record_hash`, `causal_rule`, `reason_code`, `sample_class` | Yes | Trace labels | JSONL | **Line A.** Retained. `sample_class` in the preflight was `FORWARD_LIVE_SHADOW`. These labels are not PnL. |
| `position_before`, `position_after`, `exposure`, `unrealized_pnl` | Yes | Not a stop and not a day low | JSONL | **Line A.** Context. C7 does not mine them for a day low. |
| Missing-candle / pending / no-fill rows | Yes as event types (`PENDING_NEXT_BAR`, `NO_FILL`; a host gap count is not in this checkout) | Not trades | Those rows | **Line A.** Count them. Do not delete them to improve a sample. The scorer's test retains 249 synthetic `MISSING_CANDLE` rows. |

## Line A versus Line B, in one place

| Work | Where it lives | What it must not do |
|------|----------------|---------------------|
| Fees, slippage, pairing, ex-funding diagnostic, structural hash link | Line A scorer, read-only, on a file copy | Zero-fill funding. Rewrite rows. Treat `realized_pnl_cum` as C3. |
| Preset stop, `equity_at_open`, `risk_amount`, `risk_pct`, `HARD_STOP_EXIT` | Line B, new `strategy_version`, new file or new rows after T_alloc | Backfill Line A. Choose the stop from Official PnL. |
| Funding cache and `NET_PNL_INCL_FUNDING` | Future ingest after a public-rate sign lock (PR #416 is spec only, `OFFICIAL_SIGN_LOCK=NO`) | Store a gap as `0`. Score `PARTIAL`. |
| `MARK_RULE_C7_V1` equity marks | New equity series. Do not repair the legacy 6/10-column CSV in place | Call an OHLC adverse extreme the tick low. |
| C9 register | A governance file outside the trade ledger | Treat a missing file as four zeros. |
| Capital-allocation / 0.5% sizing | Line B at an explicit T_alloc | Resize historical `quantity`. |

## What the scorer refuses to open

The program reads a regular file with a read-only open. It refuses a path whose resolved name contains `affl-v2-official-ledger`, `anchor-official-ledger`, or `/var/lib/private`. It refuses a symlink. It does not `chmod` or `setfacl` any directory. It does not write the input.

## Official result on Line A before freeze

With no T0, every windowed criterion is `NOT_SCORABLE` / `T0_NOT_FROZEN`.

With a T0, on a Line A file that still matches the preflight:

| Criterion | Status | Why |
|-----------|--------|-----|
| C1 | Scorable from the signature timestamps | Not a ledger column |
| C2 | Scorable | Pair fills; no `trade_id` required |
| C3 | `NOT_SCORABLE_ON_LINE_A` | Funding is `MISSING` |
| C4 | `NOT_SCORABLE` | Official net is C3's net |
| C5 | Scorable from `net_liquidation_equity` | Event curve, not ticks; stored `drawdown` ignored |
| C6 | `NOT_SCORABLE_ON_LINE_A` | No preset stop, no `equity_at_open`, no `risk_amount` |
| C7 | `NOT_SCORABLE_ON_LINE_A` | No `MARK_RULE_C7_V1` day open / day low |
| C8 | `NOT_SCORABLE` | Same official net as C3 |
| C9 | `NOT_SCORABLE_ON_LINE_A` | No incident register on the trade file |
| C10 | Structural link can FAIL; published status stays `NOT_SCORABLE` when the link holds | Payload hash recipe is not in this repo |
| R0 | Official comparison `NOT_SCORABLE_ON_LINE_A` | Needs the funding-inclusive net. Ex-funding diagnostic is labeled `not_a_score` |

`overall` is `NOT_ELIGIBLE` until every criterion is `PASS`. That block is not a license to invent the missing fields.

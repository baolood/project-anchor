# Official Fake-Fill Line A scoring-field gap

**Document ID:** `ANCHOR_OFFICIAL_FAKE_FILL_LINE_A_SCORING_FIELD_GAP_V1`  
**Status:** inventory. Not a grade. The pass line is FROZEN at T0 `2026-10-22T20:27:21+08:00`.  
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
| `funding_pnl` | Key yes, value null in the preflight | Yes, from a verified public cache, for hours the leg was held | Ledger status `MISSING`. Derived source `EXTERNAL_PUBLIC_FUNDING_V1` (not ledger-recorded). Absolute Kraken `fundingRate` × quantity × recorded `contract_size` × overlap hours. Short receives a positive rate. | **Line A.** Do not zero-fill. A missing hour in the hold keeps the trade `MISSING` and keeps C3, C4, C8, and R0 `NOT_SCORABLE` if any counted trade is `MISSING`. `PRESENT` plus amount `0` is a real zero. `PARTIAL` is not summed and is not replaced by the cache. Ledger PRESENT that disagrees with the cache is not averaged. |
| `fill_time_utc` | Yes on `OPEN`, `REVERSE_ENTRY`, `FLAT_EXIT`, `REVERSE_EXIT`; null on other types | Yes, as the fill clock | Those four event types | **Line A.** Entry and exit times. Other event types are not fills. |
| `signal_available_at` | Yes | Yes, as the signal clock | All preflight event types | **Line A.** T0 signal filter when the key exists. Latency diagnostic. Not a fill price. |
| `signal_candle_open_utc` | Yes | Not a fill | All preflight event types | **Line A.** Retained. Not used as fill time or fill price. |
| `effective_price` | Yes (key in the 41) | Yes, as the fill price when the row is a fill | Fill rows | **Line A.** R0 price path. |
| `signal_price`, `reference_price` | Yes | No as a fill | Fill and signal rows | **Line A.** Not substituted for `effective_price`. They are prices from before the fill, or a reference the fill rule already consumed. |
| `side`, `quantity` | Yes | Yes | Entry row | **Line A.** Pairing and R0. Quantity is copied, not resized. |
| `notional`, `fill_notional` | Yes | Not as risk and not as a new size | Entry row | **Line A.** Historical size. A later capital-allocation rule needs its own T_alloc on Line B. |
| `trade_id` | No | No as a stored id | File order plus `ledger_event_id` | **Line A.** Pair in append order. Do not write `trade_id` back onto old rows. **Line B** may store `tr_` + entry id on new rows only. |
| `preset_stop_price` (also any `stop_price` / `stop_loss`) | No | No | Absent from JSONL and from `LedgerEvent` in the preflight | **Line B only (C6).** Not a Line A gap that blocks the research baseline. Do not back-calculate a stop from later prices or from realized loss. Threshold stays 0.5%. |
| `equity_at_open` | No literal | No | `OPEN.net_liquidation_equity` is a different field | **Line B only (C6).** Do not alias the equity column. The readiness note's proxy is refused. |
| `risk_amount`, `risk_pct` | No | No | Would need a preset stop and equity at open, both absent | **Line B only (C6).** Do not infer risk from notional, from `10000` starting equity, or from outcome PnL. |
| `net_liquidation_equity` | Yes | Yes, as curve points for C5 only | JSONL events | **Line A.** C5 recomputes peak-to-trough on `[T0, T_score]`. Fills use `fill_time_utc`. Other rows use `signal_available_at`. |
| Stored `drawdown` | Yes | No for the post-T0 maximum | Row value can include a pre-T0 peak | **Line A.** Ignore the stored column. Recompute C5. |
| CST `day_open` / `day_low` | No | No | `MARK_RULE_C7_V1` marks are not on Line A | **Line B only (C7).** On Line A, C7 is `NOT_APPLICABLE`, not a research failure and not a pass. On Line B the 2% bar is unchanged and stays `NOT_SCORABLE` until the marks exist. `FLAT_MARK` is not an intraday low. An `OHLC_ADVERSE_PROXY` labeled `NOT_TICK_LOW` is not the day low. |
| Governance incident counts | No | No | Separate append-only JSONL, not the trade ledger. Procedure: `docs/PROJECT_ANCHOR_C9_GOVERNANCE_REGISTER_PROCEDURE_V1.md`. Template: `docs/templates/ANCHOR_C9_GOVERNANCE_REGISTER_TEMPLATE.jsonl`. | **Line A and Line B.** Absence or an empty file is `NOT_SCORABLE`, not `0`. PASS needs zero in-window `BREACH` rows and one Founder `ATTEST_COVERAGE` with JSON boolean `founder_signed: true` covering `[T0, T_score]`. Same hash recipe, genesis `GOVERNANCE_GENESIS`. PR #416 lists future paths and does not create the register. |
| `prev_hash`, `row_hash` | Yes | Yes, by the vendored Official V2 recipe | JSONL | **Line A and Line B.** C10 PASSes only when every row recomputes, links from `GENESIS`, `le-N` ids start at 1 and step by 1, and nothing is unparsed. Recipe: `eval_scoring/official_v2_row_hash.py`. Re-check it if the writer changes. |
| `ledger_event_id` | Yes | Identity of the row, not of the trade | JSONL | **Line A.** Unique, and `le-N` must step by 1. A gap FAILs C10. The id is not rewritten to hide a missing row. |
| `realized_pnl_cum` | Yes | No as C3 | Last-row cumulative | **Line A.** Includes the pre-T0 book and is not the paired post-T0 official net. |
| `observation_id`, `source_record_hash`, `causal_rule`, `reason_code`, `sample_class` | Yes | Trace labels | JSONL | **Line A.** Retained. `sample_class` in the preflight was `FORWARD_LIVE_SHADOW`. These labels are not PnL. |
| `position_before`, `position_after`, `exposure`, `unrealized_pnl` | Yes | Not a stop and not a day low | JSONL | **Line A.** Context. C7 does not mine them for a day low. |
| Missing-candle / pending / no-fill rows | Yes as event types (`PENDING_NEXT_BAR`, `NO_FILL`; a host gap count is not in this checkout) | Not trades | Those rows | **Line A.** Count them. Do not delete them to improve a sample. The scorer's test retains 249 synthetic `MISSING_CANDLE` rows. |

## Line A versus Line B, in one place

| Work | Where it lives | What it must not do |
|------|----------------|---------------------|
| Fees, slippage, pairing, ex-funding diagnostic, recomputed hash link, public-funding cache | Line A scorer, read-only, on a file copy plus an `EXTERNAL_PUBLIC_FUNDING_V1` cache | Zero-fill funding. Rewrite rows. Treat `realized_pnl_cum` as C3. Fetch from inside the scorer. |
| Preset stop, `equity_at_open`, `risk_amount`, `risk_pct`, `HARD_STOP_EXIT`, C6, C7 | Line B, new `strategy_version`, new file or new rows after T_alloc | Backfill Line A. Choose the stop from Official PnL. Treat a Line A research pass as real-money eligibility. |
| Funding cache | Hashed public input. Derived, not ledger-recorded. PR #416 remains off the formal scoring chain | Store a gap as `0`. Score `PARTIAL`. Average a ledger amount with the public amount. |
| `MARK_RULE_C7_V1` equity marks | New equity series. Do not repair the legacy 6/10-column CSV in place | Call an OHLC adverse extreme the tick low. |
| C9 register | A governance file outside the trade ledger, hashed with genesis `GOVERNANCE_GENESIS` | Treat a missing or empty file as four zeros. Append it onto the trade ledger. Treat the template row as a real attestation. |
| Capital-allocation / 0.5% sizing | Line B at an explicit T_alloc | Resize historical `quantity`. |

## What the scorer refuses to open

The program reads a regular file with a read-only open. It refuses a path whose resolved name contains `affl-v2-official-ledger`, `anchor-official-ledger`, or `/var/lib/private`. It refuses a symlink. It does not `chmod` or `setfacl` any directory. It does not write the input.

## Official result on Line A before freeze

With no T0, windowed research criteria are `NOT_SCORABLE` / `T0_NOT_FROZEN`. C6 and C7 on Line A are `NOT_APPLICABLE` / `LINE_B_ONLY` even then.

With a T0, on a Line A file that still matches the preflight and has no public-funding cache:

| Criterion | Status | Why |
|-----------|--------|-----|
| C1 | Scorable from the signature timestamps | Not a ledger column |
| C2 | Scorable | Pair fills; no `trade_id` required |
| C3 | `NOT_SCORABLE_ON_LINE_A` until every counted trade has PRESENT funding | Ledger funding is `MISSING`. A complete `EXTERNAL_PUBLIC_FUNDING_V1` cache makes this scorable. One missing settlement keeps it `NOT_SCORABLE`. |
| C4 | Same block as C3 | Official net is C3's net |
| C5 | Scorable from `net_liquidation_equity` | Event curve, not ticks; stored `drawdown` ignored |
| C6 | `NOT_APPLICABLE` / `LINE_B_ONLY` | Not a Line A criterion. Threshold 0.5% is unchanged and is scored only on Line B |
| C7 | `NOT_APPLICABLE` / `LINE_B_ONLY` | Not a Line A criterion. Threshold 2% is unchanged and is scored only on Line B |
| C8 | Same block as C3 | Needs the funding-inclusive net |
| C9 | Scorable when a separate register is supplied. Absent = `GOVERNANCE_REGISTER_ABSENT`. Empty = `EMPTY_GOVERNANCE_REGISTER`. Both are `NOT_SCORABLE`, not zero. PASS = 0 in-window breaches plus a Founder attestation covering the window | The Official register does not exist yet. It starts at T0. This checkout did not score one |
| C10 | Scorable. PASS only if every `row_hash` recomputes, the link from `GENESIS` holds, `le-N` ids are contiguous from 1, and unparsed lines are 0 | The Official JSONL rows are not in this checkout. The 808/808 recompute below is the Founder's evidence, not a grade produced here |
| R0 | Same block as C3 | Binding on Line A once funding is PRESENT. Ex-funding diagnostic is labeled `not_a_score` |

Line A `overall` is the research baseline. It is `NOT_ELIGIBLE` until C1, C2, C3, C4, C5, C8, C9, C10, and R0 are `PASS`. `pilot_eligible` stays false. A Line A pass is not real-money eligibility. That still requires Line B, including C6 and C7. None of this is a license to invent the missing fields.

Hash evidence, not a grade: on 2026-10-22 the Founder recomputed the vendored recipe read-only over a 2026-10-10 copy of the ledger (808 rows). Result: 808/808 `row_hash` match, 0 link breaks. This checkout does not contain that copy, so the scorer did not repeat the count. Bundle `engine.py` SHA-256 `299569516edda10e6464246457a5d3e6149ac56900fac04be90fd5fbcef1d1c8`. r2.2 candidate `engine.py` SHA-256 `cd40e5a4186dd3314450388b91a30f06176d97040236a111f5a2093de3506e45`. The four hash functions are byte-identical. Genesis is `GENESIS`.

A JSONL copy may begin with one label line. The scorer skips that one leading non-JSON line when a cell is `ledger_event_id`, `event_type`, `row_hash`, `prev_hash`, `event_id`, or `event_hash`, does not hash it, and reports `header_rows_skipped`. The first event row must still have `prev_hash` = `GENESIS`. A later non-JSON line FAILs C10. MCP `header_row_mismatches` is a different counter: it counts equity-CSV rows whose width differs from the CSV header. The scorer does not read that CSV. A 2026-10-22 summary reported `header_row_mismatches: 0`. Re-check the vendored hash file if the writer changes.

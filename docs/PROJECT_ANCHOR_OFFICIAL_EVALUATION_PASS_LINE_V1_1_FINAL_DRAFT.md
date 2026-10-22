# PROJECT ANCHOR OFFICIAL EVALUATION PASS LINE V1.1

**Document status:** FROZEN.  
**Document ID:** `ANCHOR_OFFICIAL_PASS_LINE_V1_1_FINAL_DRAFT`  
**Supersedes:** `ANCHOR_OFFICIAL_PASS_LINE_V1` (freeze candidate R2, 2026-09-30, never signed)  
**Prepared:** 2026-10-22  
**Purpose:** Research baseline for Line A, and the Pilot-request gate only when Line B passes, including C6 and C7.  
**Not a purpose:** Proof of long-term profitability. A grade of the pre-T0 book. Authorization to trade.  
**Universe:** Official Fake-Fill ledger V2, kind `official_fake_fill_v2`, file `anchor_fake_fill_ledger_v2_official.jsonl`.  
**Line A:** The sealed series already on disk. Graded on C1, C2, C3, C4, C5, C8, C9, C10, and R0. A Line A pass is not Pilot eligibility and is not real-money eligibility by itself.  
**Line B:** The separate stop-loss series (PR #417, `affl_v2_c6_protective_v1` / `official_ledger_c6_v1`). C6 (per-trade risk 0.5%) and C7 (daily loss 2%) apply only here. Real-money eligibility requires Line B passing, including C6 and C7.  
**Live trading:** **NO-GO**. Passing this document does not authorize orders, testnet sends, or a Pilot. Pilot start remains a separate Founder EXECUTE.  
**This change:** docs and an offline scorer only. It does not deploy, does not open the ledger StateDirectory, and does not append or rewrite ledger rows.

Scorer: `scripts/score_official_fake_fill_pass_line.py`  
Field inventory: `docs/PROJECT_ANCHOR_OFFICIAL_FAKE_FILL_LINE_A_SCORING_FIELD_GAP_V1.md`  
Sign-off page (FROZEN; SHA fields say `see freeze record`): `docs/PROJECT_ANCHOR_OFFICIAL_EVALUATION_PASS_LINE_V1_1_SIGN_OFF.md`  
C9 register procedure: `docs/PROJECT_ANCHOR_C9_GOVERNANCE_REGISTER_PROCEDURE_V1.md`

---

## 0. What this draft keeps, and what it adds

V1 R2 thresholds are unchanged. They were not refit to the ledger's cumulative figure.

| ID | V1 R2 threshold, still in force |
|----|----------------------------------|
| C1 | ≥ **90** days from T0 to T_score, partial day does not round up |
| C2 | ≥ **50** closed Fake-Fills with signal (when recorded), entry, and close all ≥ T0 |
| C3 | Net PnL **> 0** after fee, funding, and simulated slippage |
| C4 | Profit factor **> 1.10** on that same net (V1 R2 already replaced expectancy) |
| C5 | Peak-to-trough drawdown **≤ 8%** |
| C6 | Ex-ante risk **≤ 0.5%** of equity at open on every counted trade |
| C7 | Worst CST daily equity drop **≤ 2%**, intraday low, unrealized included |
| C8 | Best winning trade **≤ 25%** of the positive net pool |
| C9 | **0** unauthorized privilege, **0** unauthorized live-order attempt, **0** ledger tamper, **0** risk-gate bypass |
| C10 | Continuous ledger, each counted trade traceable, no silent rewrite |

V1.1 adds one pre-registered comparison, **R0**. It is not a change to any number above. Freezing V1.1 still requires a new T0. Pre-T0 rows stay on disk and stay out of the grade.

| ID | Comparison |
|----|------------|
| R0 | On the same entry fills, exit fills, quantities, and recorded costs, Anchor's official net beats the expected random-direction book |

A conversational summary of the 2026-09-30 draft still said "expectancy > 0". The R2 text that this draft follows had already replaced that metric with profit factor > 1.10. Section 8 records the recommendations that were **not** applied.

Binding rules carried forward from V1, with the Line A / Line B split added in this draft:

1. Line A research result: C1, C2, C3, C4, C5, C8, C9, C10, and R0 must PASS. One FAIL fails that result. There is no waiver. C6 and C7 are `NOT_APPLICABLE` on Line A (`LINE_B_ONLY`). They do not block the research baseline, and they are not treated as passed.
2. Line A passing does **not** make the book Pilot-eligible for real money. Real-money eligibility requires a separate Line B result in which every criterion, including C6 and C7, is PASS. The scorer sets `pilot_eligible` false on every Line A report.
3. C1 and C2 are conjunctive. Ninety days alone, or fifty trades alone, is not enough.
4. An official criterion that cannot be computed from recorded fields, or from the verified public-funding cache where §5 allows it, is **NOT_SCORABLE**. That blocks the result it belongs to (`overall = NOT_ELIGIBLE`). It is not a filled-in zero and it is not a back-calculated risk percentage. V1's sentence "unscorable ⇒ FAIL for Pilot eligibility" still describes the Line B block. The machine status stays `NOT_SCORABLE` so a missing field is not disguised as a measured FAIL.
5. After freeze, moving a threshold requires a new document version and a new T0. Keeping old scores while changing the bar is forbidden.
6. Trading remains NO-GO under this document alone. Line A research PASS does not change that.

---

## 1. T0, genesis, and what counts

| Clock | Meaning |
|-------|---------|
| Genesis | Account start of the existing book. The 2026-09-30 readiness note records a legacy equity seed at `2026-09-27T15:41:34Z`, label `LEDGER_GENESIS`, starting equity `10000`. That instant is **not** T0. |
| T0 | `2026-10-22T20:27:21+08:00`. Asia/Shanghai wall time of the freeze commit. |
| T_score | Grading timestamp declared by the Founder. |
| Counted trade | One paired open→close whose `signal_available_at` (when the key exists), entry `fill_time_utc`, and exit `fill_time_utc` are all inside `[T0, T_score]`. |
| Pre-freeze evidence | Every row before T0, including the book that already exists on 2026-10-22. Retained. Not graded. |

`window_days = floor((T_score − T0) / 86400)`.

A trade opened before T0 and closed after T0 is contamination. It stays in the file and is excluded from C2–C8 and R0.

The scorer's default `--t0` is this frozen value. `T_score` is still supplied at grading. A windowed criterion stays `T0_NOT_FROZEN` until `T_score` is supplied. An explicit `--t0` on one run does not move this frozen T0. The R0 seed was left blank. The expected random-direction book remains the binding comparison.

---

## 2. Line A and Line B

**Line A** is the Official V2 series already written: `OPEN`, `FLAT_EXIT`, `REVERSE_ENTRY`, `REVERSE_EXIT`, `NO_FILL`, `PENDING_NEXT_BAR`, `OBSERVATION_COMMIT`, `FLAT_MARK`, and any other row the writer appended. Its history is sealed. It is a research baseline. C6 and C7 do not apply to it.

**Line B** is any later series that records a real preset stop, `equity_at_open`, and `risk_amount` at the open, under a new `strategy_version` and a new schema. PR #417 (`affl_v2_c6_protective_v1` / `official_ledger_c6_v1`) is a candidate for that series. It is open, not merged, and not attached to the Official writer. Its rows must not be appended onto the Line A file and must not be used to rewrite Line A. C6 and C7 are scored only on Line B. The 0.5% and 2% thresholds are unchanged.

The scorer reads Line B when `--line B` is set, or when the copy's schema / strategy marker is `official_ledger_c6_v1` or `affl_v2_c6_protective_v1` and no Line A marker is mixed in. It does not invent stop, equity-at-open, or risk fields for Line A. A Line A research PASS is not a Line B pass.

---

## 3. Fill rule and program latency

The fill is the recorded fill. Decision time and program latency are different facts.

| Fact | Field | Use |
|------|--------|-----|
| Signal existed | `signal_available_at` | T0 filter when the key exists. Latency diagnostic. |
| Candle the signal refers to | `signal_candle_open_utc` | Not a fill time and not a fill price. |
| Fill happened | `fill_time_utc` on `OPEN`, `REVERSE_ENTRY`, `FLAT_EXIT`, `REVERSE_EXIT` | Entry and exit clock. |
| Fill price | `effective_price` on that fill row | Random-direction price path. |
| Pre-fill prices | `signal_price`, `reference_price` | Not substituted for `effective_price`. |
| Not a fill | `PENDING_NEXT_BAR`, `NO_FILL`, `OBSERVATION_COMMIT`, `FLAT_MARK`, `MISSING_CANDLE` | Counted and retained. They do not open or close a trade. |

The scorer reports `fill_latency_seconds` with `used_as_fill: false`. Latency does not move the fill and does not change PnL.

`HARD_STOP_EXIT` is a Line B exit. If a future file contains it, the scorer pairs it. Line A as inventoried on 2026-09-30 has no such event.

---

## 4. Capital allocation is a new rule

Line A size is whatever `quantity` and `notional` the writer stored on that row. The readiness note describes a fixed active notional and a fixed starting equity in the writer config. That is not an ex-ante 0.5% risk record.

Any later capital-allocation rule, including "shrink quantity so risk stays inside 0.5%", takes effect only at an explicit timestamp **T_alloc** written into the Line B document, and only for fills at or after T_alloc. It does not resize, delete, or rescore Line A rows. The scorer copies `quantity` into the trade list and has no shrink step.

---

## 5. How each criterion is computed

Statuses are `PASS`, `FAIL`, `NOT_SCORABLE`, or, for C6 and C7 on Line A only, `NOT_APPLICABLE`. Money is decimal text. Missing funding is the string `MISSING`.

Pairing is file order, which is append order. `OPEN` or `REVERSE_ENTRY` while flat starts a leg. The next `FLAT_EXIT`, `REVERSE_EXIT`, or `HARD_STOP_EXIT` closes it. A second open while a leg is open, or an exit while flat, makes pairing unfair: C2–C4, C8, and R0 stay `NOT_SCORABLE` with reason `PAIRING_NOT_FAIR`. On Line B, C6 does too. The rows are not dropped.

### C1 — Observation window

**Line A today:** scorable once T0 and T_score exist. They are signature fields, not ledger columns.  
**Until freeze:** `NOT_SCORABLE` / `T0_NOT_FROZEN`.  
**PASS** when `window_days ≥ 90`.

### C2 — Closed trades after T0

**Line A:** scorable from `event_type` and `fill_time_utc`, plus `signal_available_at` when that key is present. There is no `trade_id` on Line A. Identity is the pair of `ledger_event_id`s.  
**PASS** when the counted set has at least 50 trades.  
**FAIL** when the count is below 50.  
An open leg at end of file is not a closed trade.

### C3 — Net PnL after costs

Per counted trade:

```text
exit_leg = exit.NET_PNL_EX_FUNDING
           (exit.net_pnl only when it is the same number)
net_ex_funding = exit_leg − entry.fee_paid − entry.slippage_cost
official_net   = net_ex_funding + funding_pnl
                 only when that trade's funding status is PRESENT
```

The exit leg excludes entry costs. `realized_pnl_cum` is not this sum. A stored `0` is a real zero only when status is `PRESENT` and the amount is `0`. Null, absent, `MISSING`, or `PARTIAL` stays `MISSING` and is not added.

Funding becomes PRESENT in either of two ways:

1. The exit row already has `FUNDING_DATA_STATUS = PRESENT` and a finite `funding_pnl`. That amount is ledger-recorded. If a public cache is also supplied and its amount for the same hold differs by more than `1e-8`, the trade is `FUNDING_LEDGER_EXTERNAL_DISAGREE`. The two amounts are not averaged.
2. The exit row is `MISSING` and every settlement inside the hold is present in a verified `EXTERNAL_PUBLIC_FUNDING_V1` cache. The scorer then uses the derived amount and labels the source `EXTERNAL_PUBLIC_FUNDING_V1`. That label means derived from public rates, not written on the ledger.

`PARTIAL` and `NO_INTERVAL` on the ledger are not replaced by the cache.

**Public funding method.** Cache file `eval_scoring/public_funding.py`, fetched only by `scripts/fetch_public_funding_cache.py`. The scorer never fetches. Locked URL:

`https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=SYMBOL`

Checked on 2026-10-22 for `PF_XBTUSD`. The v3 unhyphenated path is HTTP 404. The v4 hyphenated and v4 unhyphenated paths also return the same shape. The cache records the URL that was fetched.

- `fundingRate` is absolute USD that a 1-contract short receives for one full hour. Positive means longs pay shorts. Negative reverses that.
- `relativeFundingRate` is audit-only. It is not multiplied by notional or by the entry price. Doing so would use the wrong price: the absolute rate already embeds spot at calculation time.
- `timestamp` is the start of the hour the rate applies to. The window is `[timestamp, timestamp + 1 hour)`. The next stamp is not the period length, so a gap is not hidden.
- A held leg is `[entry fill_time_utc, exit fill_time_utc)`. Overlap is prorated. Kraken realizes funding at the hour end or when the position changes, so a partial hour closed before the clock settlement still counts.
- Only clock hours that overlap that hold are summed. One missing hour makes the whole leg `MISSING`. No partial sum is kept. A cached rate of `0` is a real zero.
- Payout = `short_sign × quantity × contract_size × fundingRate × overlap_hours`. Short sign is +1 for a short and −1 for a long.
- `contract_size` is stored on the cache from `https://futures.kraken.com/derivatives/api/v3/instruments`. For `PF_XBTUSD` that field was `1` on 2026-10-22 (base BTC, quote USD, tick size 1). Ledger `quantity` is multiplied by the stored size. The scorer does not look up a size at score time.
- The instrument is the ledger `market` / `symbol` / `instrument` / `product_id` when those keys exist. A row value that disagrees with the cache symbol is `FUNDING_INSTRUMENT_MISMATCH`. Several instruments on one file, with the market absent on the leg, is `FUNDING_MULTIPLE_INSTRUMENTS`. If no row carries an instrument, the cache symbol is used and the report says `CACHE_SYMBOL_LEDGER_MARKET_ABSENT`. That is a label, not a silent assumption.
- The cache embeds `rates_sha256` over the canonical sorted rate list (timestamp, fundingRate, and relativeFundingRate when present). A mismatch is a refusal, not a score. The report also records the SHA-256 of the cache file bytes, the source URL, and `fetched_at`.

The live public history has occasional multi-hour gaps. A leg held across a gap stays `MISSING` until a cache actually contains that hour. Do not interpolate.

When `gross_pnl` and all four fee and slippage amounts are present, the scorer recomputes `gross_pnl − entry fee − entry slippage − exit fee − exit slippage`. Disagreement beyond `1e-8` yields `NET_AND_GROSS_INCONSISTENT`. The two figures are not averaged.

**Line A without a covering cache, and with ledger funding still `MISSING`:** `NOT_SCORABLE` / `NOT_SCORABLE_ON_LINE_A`. The 2026-09-30 preflight found `funding_pnl` null and `FUNDING_DATA_STATUS = MISSING` on every event, with `NET_PNL_STATUS = EX_FUNDING`. Fee and slippage keys exist. The scorer still prints `diagnostic_ex_funding`, marked `not_a_score: true`. That diagnostic is not C3.

**With funding PRESENT on every counted trade:** C3, C4, C8, and R0 are scorable. **PASS** only when the summed official net is `> 0`. If any counted trade is still `MISSING`, those four stay `NOT_SCORABLE`.

### C4 — Profit factor

Uses the official nets from C3.

```text
PF = sum(positive official nets) / abs(sum(negative official nets))
```

No losing trade, a positive winning pool, and C3 PASS: V1 special case PASS, value `UNDEFINED_NO_LOSSES`. A zero winning pool FAILs. `PF = 1.10` FAILs. The bar is strict `>`.

**Line A:** scorable once every counted trade has PRESENT funding, from the ledger or from a complete public cache. Otherwise `NOT_SCORABLE` / `C3_NET_UNAVAILABLE`.

### C5 — Maximum drawdown

```text
points = recorded net_liquidation_equity with a time in [T0, T_score]
fill rows use fill_time_utc
other rows use signal_available_at
max_dd = max (peak_so_far − equity) / peak_so_far
```

The row's own `drawdown` column is ignored. It can include a pre-T0 peak. At least two points are required. A non-positive peak is `NOT_SCORABLE`.

**Line A:** scorable from `net_liquidation_equity` once T0 exists. This is the recorded event curve, not a tick curve. The 8% bar is still the V1 bar. The legacy equity CSV is not read: its 6-column header does not match the 10-column body (readiness note, 2026-09-30).

### C6 — Per-trade risk

```text
risk_pct = entry.risk_amount / entry.equity_at_open
```

The entry must also contain `preset_stop_price`. The stop price is not turned into a risk amount by this program. Outcome PnL is not a stop. `net_liquidation_equity` on the OPEN row is not `equity_at_open`.

**Applies to Line B only.** The threshold stays 0.5%. On Line A the status is `NOT_APPLICABLE` / `LINE_B_ONLY`, including before T0 is frozen. That is not a pass, and it is not a research-baseline failure. The preflight found no stop key and no risk key on Line A; those fields are not back-calculated.

**Line B:** `FAIL` when the three fields are present and some counted trade is above 0.5%. Equality with 0.5% passes. Missing fields on Line B are `NOT_SCORABLE` / `EX_ANTE_FIELDS_MISSING`.

### C7 — Daily equity drop

A CST day counts only under `MARK_RULE_C7_V1`:

- `mark_kind` is `BAR_1H`, `FILL`, or `GENESIS`
- `mark_honesty_label` is not `NOT_TICK_LOW` (an OHLC adverse proxy is not the day low)
- T0's calendar day opens at a mark **at T0**, not at CST midnight of that partial day
- Each later day opens at a mark **at 00:00 Asia/Shanghai**
- `day_low` is the minimum qualifying mark from that open through the next midnight, or through T_score on the last day
- `daily_loss = (day_open − day_low) / day_open`

`FLAT_MARK` rows without that rule are not a day low. Using them would understate the drop and would be a guess.

**Applies to Line B only.** The threshold stays 2%. On Line A the status is `NOT_APPLICABLE` / `LINE_B_ONLY`. Line A is not failed for lacking `MARK_RULE_C7_V1` marks, and it is not passed on that criterion either. On Line B, absent marks are `NOT_SCORABLE` / `MARK_RULE_C7_V1_ABSENT`. A measured daily loss above 2% is `FAIL`.

### C8 — Profit concentration

```text
share = max(winning official nets) / sum(positive official nets)
```

**Line A:** same funding rule as C3. Scorable when every counted trade has PRESENT funding. Otherwise `NOT_SCORABLE`.  
**PASS** when the pool is positive and `share ≤ 0.25`.

### C9 — Governance incidents

Incident counts are not columns on the trade ledger. They live in a separate append-only JSONL that starts at T0. The procedure, the field list, and the template are `docs/PROJECT_ANCHOR_C9_GOVERNANCE_REGISTER_PROCEDURE_V1.md` and `docs/templates/ANCHOR_C9_GOVERNANCE_REGISTER_TEMPLATE.jsonl`. PR #416 names future host paths and does not create this register. That PR is not on the formal scoring chain. Do not append governance rows onto the trade ledger.

Each row is `BREACH` or `ATTEST_COVERAGE`. The hash is the same Official V2 recipe as C10, with its own genesis `GOVERNANCE_GENESIS` (not `GENESIS`). Ids are `gov-N`, start at 1, and step by 1.

An absent file is `NOT_SCORABLE` / `GOVERNANCE_REGISTER_ABSENT`. An empty file is `NOT_SCORABLE` / `EMPTY_GOVERNANCE_REGISTER`. Neither is four zeros.

A hash-chain break or a row-hash mismatch is **FAIL** (`GOVERNANCE_HASH_CHAIN_BREAK` or `GOVERNANCE_ROW_HASH_MISMATCH`). A duplicate id or an id gap is **FAIL**. A known breach is **FAIL** even when the covering attestation is missing, so a breach cannot hide as `NOT_SCORABLE`.

The scorer counts `BREACH` rows whose `time_utc` is inside `[T0, T_score]`:

- `UNAUTHORIZED_PRIVILEGE`
- `UNAUTHORIZED_LIVE_ORDER`
- `LEDGER_TAMPER`
- `RISK_GATE_BYPASS`
- any other named rule, counted as `OTHER`

**PASS** only when every one of those counts is 0 and one `ATTEST_COVERAGE` row has JSON boolean `founder_signed: true` (the string `"true"` does not count) with `window_start ≤ T0` and `window_end ≥ T_score`. Zero breaches without that Founder row is `NOT_SCORABLE` / `GOVERNANCE_COVERAGE_NOT_ATTESTED`.

The threshold text stays `0/0/0/0`. The register starts empty at T0. It is not backfilled from pre-T0 notes.

### C10 — Ledger integrity

**PASS** only when all of the following hold:

- zero unparsed lines
- at least one event row
- every recomputed `row_hash` matches the stored `row_hash`
- each `prev_hash` equals the previous row's `row_hash`, and the first event row's `prev_hash` is `GENESIS`
- `ledger_event_id` is present, unique, matches `le-N`, starts at 1, and steps by 1

A payload change that is not re-hashed is **FAIL** / `ROW_HASH_MISMATCH`. A broken link is **FAIL** / `HASH_CHAIN_BREAK`. A duplicate id is **FAIL** / `DUPLICATE_LEDGER_EVENT_ID`. A gap, or a first id that is not 1, is **FAIL** / `LEDGER_EVENT_ID_GAP`. An id that is not `le-N` is **FAIL** / `LEDGER_EVENT_ID_NOT_CONTIGUOUS`. An unparsed line is **FAIL** / `UNPARSED_ROWS`. An empty event list is `NOT_SCORABLE` / `EMPTY_LEDGER`.

The recipe is vendored, read-only, in `eval_scoring/official_v2_row_hash.py`. It is the `canonical_json` / `sha256_hex` / `_row_body_for_hash` / `compute_row_hash` text from `affl_v2/engine.py` in the Mac Official runner bundle `affl-v2-official-auto-ingest-runtime.tgz`.

| Source | SHA-256 |
|--------|---------|
| Bundle `engine.py` | `299569516edda10e6464246457a5d3e6149ac56900fac04be90fd5fbcef1d1c8` |
| r2.2 deploy-candidate `engine.py` | `cd40e5a4186dd3314450388b91a30f06176d97040236a111f5a2093de3506e45` |

Those four functions are byte-identical across the two files. `GENESIS_PREV_HASH` is `affl_v2/config.py` line 130: `GENESIS`. Canonical JSON is `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))`, then SHA-256 of the UTF-8 text. The hash body is every field except `row_hash`, with `prev_hash` set to the chain previous. Re-check the vendored copy if the writer changes. A later writer hash is not this recipe.

Evidence, recorded from the Founder on 2026-10-22: this recipe, recomputed read-only over a 2026-10-10 copy of the ledger (808 rows), matched 808/808 `row_hash` values and found 0 link breaks. This checkout does not contain that copy. The scorer did not repeat that count. That recompute is not a grade, and it is not a freeze.

**Header row.** MCP `header_row_mismatches` is the equity-CSV width check in `anchor-backend/app/mcp/official_ledger.py`. A later read-only summary reported `header_row_mismatches: 0`. This scorer does not open that CSV. On a JSONL copy, the parser skips at most one leading non-JSON line when a comma-separated cell is `ledger_event_id`, `event_type`, `row_hash`, `prev_hash`, `event_id`, or `event_hash`. That line is not hashed. The report field is `header_rows_skipped`. The first JSON event must still chain from `GENESIS`. A later non-JSON line is unparsed and C10 FAILs. A JSON object is never a header.

When the checks pass, `structural_status` and `payload_digest_status` are both `PASS`, and `value` is `RECOMPUTED_LINK_OK`.

### R0 — Random direction, pre-registered

Same counted trades. Gross is `exit.gross_pnl` when present. Otherwise it is `net_ex_funding + recorded fee and slippage` when those costs exist. Otherwise it is `side × (exit.effective_price − entry.effective_price) × entry.quantity`. `signal_price` and `reference_price` are not read for this.

A fair coin has expected gross 0. Funding that flips sign with side has expected value 0. Expected random-direction net = `− recorded costs`.

```text
PASS when official Anchor net > expected random-direction net
```

With funding present and equal to zero, that comparison is positive gross. It is weaker than C3 whenever costs are positive. It is still required, so a cost-identity error cannot hide inside the net. After §9 records a seed, the same net must also beat the median of 1000 seeded books. The seed is `SHA256(seed | sim | entry ledger_event_id)`; the low bit of the digest picks the same side or the opposite side, and funding flips with the side. Until a seed is frozen, `seeded_comparison` is `NOT_FROZEN` and the expected book is the binding comparison.

**Line A:** scorable when every counted trade has PRESENT funding, including funding taken from a verified `EXTERNAL_PUBLIC_FUNDING_V1` cache. Otherwise `NOT_SCORABLE` / `NOT_SCORABLE_ON_LINE_A`. `diagnostic_ex_funding` may still say whether the ex-funding book beats the expected null. That object is `not_a_score: true`. R0 remains binding on the Line A research baseline.

---

## 6. Sample size

Fifty trades and ninety days are floors from V1, not a power calculation.

A profit factor of 1.10 on fifty trades of a one-hour market has a wide sampling error. C8 stops one trade from being more than a quarter of the winning pool. It does not produce a confidence interval. Ninety days can still be one market regime, including a long stretch of `PENDING_NEXT_BAR` and `NO_FILL`.

Those floors stay. Section 8 recommends an extra report. It does not lower the floors, and it does not treat the pre-T0 book as the sample that satisfies C1 or C2.

---

## 7. Point-in-time ledger snapshot (not a grade)

Read-only MCP `get_ledger_summary` at `2026-10-22T10:41:46Z`. The mirror hash matched. This is pre-freeze evidence.

| Item | Value |
|------|--------|
| Source | `anchor_fake_fill_ledger_v2_official.jsonl` |
| Events | 1666 |
| `OPEN` | 145 |
| `FLAT_EXIT` | 144 |
| `REVERSE_ENTRY` | 22 |
| `REVERSE_EXIT` | 22 |
| `NO_FILL` | 128 |
| `PENDING_NEXT_BAR` | 462 |
| `OBSERVATION_COMMIT` | 591 |
| `FLAT_MARK` | 152 |
| Last id | `le-001666` |
| Last time | `2026-10-22T10:05:02Z` (`signal_available_at`) |
| Reported hash-chain head | `dbea89c7aee3230ea88e9ac8f6e4a28e08e4beef9a334d6fc6a73ecf66e267d5` |
| `realized_pnl_cum` | `-23.65505249094414` |

The summary's own note: per-exit `NET_PNL` excludes entry costs, and `realized_pnl_cum` is the ledger cumulative figure, not an exchange cash balance. It is not C3. One leg is unclosed (`145 + 22 − 144 − 22 = 1`). Closed legs before T0 do not count toward 50.

A few minutes earlier the file had 1664 events and 460 `PENDING_NEXT_BAR` rows. `FLAT_MARK` (152) was already inside that 1664. The two newer rows are more pending bars. This draft does not delete them.

The MCP summary does not return row keys. The field inventory in the gap document is the 2026-09-30 preflight of the live JSONL (41 keys, no stop, no `equity_at_open`, no `risk_amount`, funding null). This environment did not re-dump the file. The scorer uses only keys present on the copy it is given.

A later read-only summary at `2026-10-22T11:58:11Z` showed 1667 events, `PENDING_NEXT_BAR` 463, last id `le-001667`, hash head `c79ecbf70cb2821e517c0f84b31164386d0a3c173da5d61979735ca10a982469`, and the same `realized_pnl_cum`. The mirror sidecar checked. That call still returns no rows, so the scorer was not run on the Official file. The one new row since the table above is another pending bar. It is not deleted here. None of these figures is a grade.

---

## 8. Recommendations (not applied)

These do **not** change the thresholds in §0.

1. Keep C3's requirement that funding be present. Do not adopt "ex-funding counts as the official net." A verified `EXTERNAL_PUBLIC_FUNDING_V1` cache can supply the missing ledger amount. A settlement the cache does not contain stays `MISSING`, not zero.
2. Keep 0.5%, 8%, 2%, 25%, 90 days, 50 trades, and profit factor 1.10. The pre-T0 cumulative figure is negative and is not a reason to move any bar.
3. Keep the V1 no-loss special case for C4, and keep it conjunctive with C1 and C2.
4. The writer's `row_hash` canonicalization is now vendored for C10. Re-check `eval_scoring/official_v2_row_hash.py` against `affl_v2/engine.py` if the writer changes, and record the new file SHA-256 before any freeze that relies on it. Do not treat a writer change as already covered by the 2026-10-22 citation.
5. Add a pre-registered block-bootstrap report on the post-T0 official nets. Publish it beside the grade. Do not turn it into a new numeric gate in this draft.
6. For R0, consider also requiring Anchor's official net to beat the 95th percentile of the seeded random books, not only the expected book and the median. Not applied. The binding comparison remains the one in §5.
7. Do not loosen C7's 2%. C7 applies only to Line B. Sparse Line A `FLAT_MARK` rows are not a reason to score Line A on C7, and they are not a reason to lower the Line B bar. Line B stays unscorable until `MARK_RULE_C7_V1` marks exist.
8. Do not alias `OPEN.net_liquidation_equity` to `equity_at_open`. The readiness note called that a proxy. This draft refuses the alias.

---

## 9. Freeze signature (FROZEN)

I freeze **PROJECT ANCHOR OFFICIAL EVALUATION PASS LINE V1.1** as the research baseline for Line A and as the sole bar for requesting a minimal-capital live Pilot once Line B passes, including C6 and C7, until a numbered successor is frozen. Scoring starts at T0. Only trades whose signal (when recorded), entry, and close are all inside `[T0, T_score]` count. Line A rows are not rewritten. Line A passing does not make the book Pilot-eligible for real money. Line B, if opened later, starts at its own T_alloc and its own files. Passing does not authorize live trading.

| Field | Value |
|-------|--------|
| Freeze time T0 (Asia/Shanghai) | `2026-10-22T20:27:21+08:00` |
| T_alloc for any new capital-allocation rule | blank (no new allocation rule) |
| Founder name | baolood herid |
| Signature / mark | Founder chat confirmation 2026-10-22 20:24 Asia/Shanghai via Grok Bot |
| Document SHA-256 (**required at freeze**) | see freeze record |
| Git commit SHA of this frozen file (**required at freeze**) | see freeze record |
| R0 random-direction seed (**required at freeze if seeded median is in force**) | blank |
| `T0_FROZEN` | `YES` |

The scorer's `frozen` field is `true`. Its `frozen_t0` is the T0 above. The sign-off page SHA-256 and this freeze commit's SHA are in the freeze record, not in this table. Thresholds are unchanged. Live trading stays NO-GO.

---

## 10. How to run the scorer

From a checkout of this repository, against a **copy** of the JSONL. Do not point it at the StateDirectory (`affl-v2-official-ledger`, `anchor-official-ledger`, or `/var/lib/private`). Those paths are refused. The input is opened read-only. `--out` cannot be the ledger path.

```bash
cd /path/to/project-anchor
python3 scripts/fetch_public_funding_cache.py \
  --symbol PF_XBTUSD \
  --out /path/to/copy/external_public_funding_v1.json
python3 scripts/score_official_fake_fill_pass_line.py \
  --ledger /path/to/copy/anchor_fake_fill_ledger_v2_official.jsonl \
  --funding-cache /path/to/copy/external_public_funding_v1.json \
  --line A \
  --t0 'YYYY-MM-DDTHH:MM:SS+08:00' \
  --t-score 'YYYY-MM-DDTHH:MM:SS+08:00' \
  --governance /path/to/copy/governance.jsonl \
  --random-seed '<seed recorded in section 9>' \
  --out /path/to/score-report.json
```

`--line` defaults to A unless the copy itself carries the Line B schema. `--funding-cache` is optional. Without it, ledger `MISSING` funding stays `MISSING`. The scorer does not fetch. `--t0` defaults to `2026-10-22T20:27:21+08:00`. Omit `--t-score` until grading; windowed research criteria then say `T0_NOT_FROZEN`. `--governance` defaults to `governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl`, which is empty. An empty register is `NOT_SCORABLE`, not zero. `--random-seed` stays unset. C6 and C7 on Line A say `LINE_B_ONLY`.

Exit status 0 means a report was written. On Line A the grade is `research_baseline` (also copied to `overall`). `pilot_eligible` stays false. On Line B, `overall` includes C6 and C7, and `pilot_eligible` is true only when that overall is PASS. Exit status 2 means the path was refused, a timestamp did not parse, or the funding-cache hash did not match.

Tests:

```bash
cd /path/to/project-anchor
python3 -m unittest tests.test_score_official_fake_fill_pass_line tests.test_public_funding_v1
```

---

## 11. Repo facts that bear on these constraints

Checked in this checkout and against open PRs #416 and #417. None of these facts were "fixed" by rewriting a ledger.

| Fact | Relation to this draft |
|------|------------------------|
| V1 R2 text uses profit factor > 1.10. A short summary of that draft still said expectancy > 0. | This draft follows R2. |
| V1 says a missing required field fails eligibility. | The scorer emits `NOT_SCORABLE` and `overall = NOT_ELIGIBLE`. It does not print a fake measured FAIL. |
| Readiness note G1 said a missing stop makes C6 fail, and called `OPEN.net_liquidation_equity` a proxy for `equity_at_open`. | C6 is Line B only. On Line A it is `NOT_APPLICABLE`. The proxy is not accepted. The 0.5% bar is unchanged. |
| PR #416 is open and states `FORMAL_SCORING_CHAIN=NOT_ON_FORMAL_SCORING_CHAIN`, `OFFICIAL_SIGN_LOCK=NO`, and missing funding stays `EX_FUNDING`. | This draft does not adopt that PR. Public funding is a separate derived input, `EXTERNAL_PUBLIC_FUNDING_V1`, and a missing settlement stays `MISSING`. That PR does not close C9 or C10. |
| PR #417 is open, `DEPLOY=NO`, new `strategy_version`, and it does not load a prior Official ledger. | That is Line B material. It is not merged and must not be backfilled onto Line A. |
| `affl_v2` writer code is not imported by this repository. The hash functions are a read-only vendor of `affl_v2/engine.py` (bundle SHA-256 `299569516edda10e6464246457a5d3e6149ac56900fac04be90fd5fbcef1d1c8`; r2.2 candidate SHA-256 `cd40e5a4186dd3314450388b91a30f06176d97040236a111f5a2093de3506e45`). Genesis is `GENESIS` from `affl_v2/config.py` line 130. | C10 recomputes with that copy. Re-vendor if the writer changes. The fee formula is still the ledger's own per-exit note: exit net excludes entry costs. |
| Legacy equity CSV header is 6 columns and the body is 10. | The scorer does not read that CSV. |
| `docs/GO_LIVE_CHECKLIST.md` records live trading **NO-GO**. The live MCP status on 2026-10-22 also reports `live_trading: NO-GO` and `go_live: NO-GO`. | Consistent with this draft. A pass line PASS would still not authorize orders. |
| MCP `net_pnl_note` says per-exit NET_PNL excludes entry costs. | The C3 formula subtracts entry `fee_paid` and entry `slippage_cost`. |
| No file in this checkout contains a count of 249 missing-candle events. | The retention rule is still in the scorer: every row is counted, including `MISSING_CANDLE`, and nothing is deleted. A unit test locks a 249-row gap set. If that count exists only on the host ledger, this PR does not touch it. |
| Open PR #426 collapses repeated `PENDING_NEXT_BAR` rows on a read-side summary. | This scorer does not collapse or drop those rows. A display collapse is not a license to rewrite the file. |

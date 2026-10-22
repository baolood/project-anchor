# PROJECT ANCHOR OFFICIAL EVALUATION PASS LINE V1.1

**Document status:** FINAL DRAFT. Not frozen. Not binding.  
**Document ID:** `ANCHOR_OFFICIAL_PASS_LINE_V1_1_FINAL_DRAFT`  
**Supersedes, once frozen:** `ANCHOR_OFFICIAL_PASS_LINE_V1` (freeze candidate R2, 2026-09-30, never signed)  
**Prepared:** 2026-10-22  
**Purpose:** Gate for whether Anchor may *request* a minimal-capital live Pilot.  
**Not a purpose:** Proof of long-term profitability. A grade. Authorization to trade.  
**Universe:** Official Fake-Fill ledger V2, kind `official_fake_fill_v2`, file `anchor_fake_fill_ledger_v2_official.jsonl`.  
**Line scored:** **Line A**, the sealed series already on disk. Stop-loss and ex-ante risk belong to a future **Line B** with its own records.  
**Live trading:** **NO-GO**. Passing this document does not authorize orders, testnet sends, or a Pilot. Pilot start remains a separate Founder EXECUTE.  
**This change:** docs and an offline scorer only. It does not deploy, does not open the ledger StateDirectory, and does not append or rewrite ledger rows.

Scorer: `scripts/score_official_fake_fill_pass_line.py`  
Field inventory: `docs/PROJECT_ANCHOR_OFFICIAL_FAKE_FILL_LINE_A_SCORING_FIELD_GAP_V1.md`

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

Binding rules carried forward from V1:

1. All of C1–C10 and R0 must PASS. One FAIL fails the exam. There is no waiver.
2. C1 and C2 are conjunctive. Ninety days alone, or fifty trades alone, is not enough.
3. An official criterion that cannot be computed from recorded fields is **NOT_SCORABLE**. That blocks eligibility (`overall = NOT_ELIGIBLE`). It is not a filled-in zero and it is not a back-calculated risk percentage. V1's sentence "unscorable ⇒ FAIL for Pilot eligibility" still describes the block. The machine status stays `NOT_SCORABLE` so a missing field is not disguised as a measured FAIL.
4. After freeze, moving a threshold requires a new document version and a new T0. Keeping old scores while changing the bar is forbidden.
5. Trading remains NO-GO under this document alone.

---

## 1. T0, genesis, and what counts

| Clock | Meaning |
|-------|---------|
| Genesis | Account start of the existing book. The 2026-09-30 readiness note records a legacy equity seed at `2026-09-27T15:41:34Z`, label `LEDGER_GENESIS`, starting equity `10000`. That instant is **not** T0. |
| T0 | Asia/Shanghai wall time when the Founder freezes this file. Blank until §9 is signed. |
| T_score | Grading timestamp declared by the Founder. |
| Counted trade | One paired open→close whose `signal_available_at` (when the key exists), entry `fill_time_utc`, and exit `fill_time_utc` are all inside `[T0, T_score]`. |
| Pre-freeze evidence | Every row before T0, including the book that already exists on 2026-10-22. Retained. Not graded. |

`window_days = floor((T_score − T0) / 86400)`.

A trade opened before T0 and closed after T0 is contamination. It stays in the file and is excluded from C2–C8 and R0.

The scorer prints `T0_NOT_FROZEN` for every windowed criterion until both timestamps are supplied. Supplying them on the command line does not freeze this document.

---

## 2. Line A and Line B

**Line A** is the Official V2 series already written: `OPEN`, `FLAT_EXIT`, `REVERSE_ENTRY`, `REVERSE_EXIT`, `NO_FILL`, `PENDING_NEXT_BAR`, `OBSERVATION_COMMIT`, `FLAT_MARK`, and any other row the writer appended. Its history is sealed.

**Line B** is any later series that records a real preset stop, `equity_at_open`, and `risk_amount` at the open, under a new `strategy_version` and a new schema. PR #417 (`affl_v2_c6_protective_v1` / `official_ledger_c6_v1`) is a candidate for that series. It is open, not merged, and not attached to the Official writer. Its rows must not be appended onto the Line A file and must not be used to rewrite Line A.

The scorer will read Line B fields when they are actually present on the copy it is given. It will not invent them for Line A.

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

Statuses are `PASS`, `FAIL`, or `NOT_SCORABLE`. Money is decimal text. Missing funding is the string `MISSING`.

Pairing is file order, which is append order. `OPEN` or `REVERSE_ENTRY` while flat starts a leg. The next `FLAT_EXIT`, `REVERSE_EXIT`, or `HARD_STOP_EXIT` closes it. A second open while a leg is open, or an exit while flat, makes pairing unfair: C2–C4, C6, C8, and R0 stay `NOT_SCORABLE` with reason `PAIRING_NOT_FAIR`. The rows are not dropped.

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
official_net   = net_ex_funding + exit.funding_pnl
                 only when exit.FUNDING_DATA_STATUS = PRESENT
                 and exit.funding_pnl is a finite number
```

The exit leg excludes entry costs. `realized_pnl_cum` is not this sum. A stored `0` is a real zero only when status is `PRESENT` and the amount is `0`. Null, absent, `MISSING`, or `PARTIAL` stays `MISSING` and is not added.

When `gross_pnl` and all four fee and slippage amounts are present, the scorer recomputes `gross_pnl − entry fee − entry slippage − exit fee − exit slippage`. Disagreement beyond `1e-8` yields `NET_AND_GROSS_INCONSISTENT`. The two figures are not averaged.

**Line A today:** `NOT_SCORABLE` / `NOT_SCORABLE_ON_LINE_A`. The 2026-09-30 preflight found `funding_pnl` null and `FUNDING_DATA_STATUS = MISSING` on every event, with `NET_PNL_STATUS = EX_FUNDING`. Fee and slippage keys exist. The scorer still prints `diagnostic_ex_funding`, marked `not_a_score: true`. That diagnostic is not C3.

**PASS** only when every counted trade has a PRESENT funding amount and the summed official net is `> 0`.

### C4 — Profit factor

Uses the official nets from C3.

```text
PF = sum(positive official nets) / abs(sum(negative official nets))
```

No losing trade, a positive winning pool, and C3 PASS: V1 special case PASS, value `UNDEFINED_NO_LOSSES`. A zero winning pool FAILs. `PF = 1.10` FAILs. The bar is strict `>`.

**Line A today:** `NOT_SCORABLE` / `C3_NET_UNAVAILABLE`, because the official net needs funding.

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

**Line A today:** `NOT_SCORABLE` / `NOT_SCORABLE_ON_LINE_A`. The preflight found no stop key and no risk key in the JSONL or in `LedgerEvent`.  
**FAIL** only when the three fields are present and some counted trade is above 0.5%. Equality with 0.5% passes.

### C7 — Daily equity drop

A CST day counts only under `MARK_RULE_C7_V1`:

- `mark_kind` is `BAR_1H`, `FILL`, or `GENESIS`
- `mark_honesty_label` is not `NOT_TICK_LOW` (an OHLC adverse proxy is not the day low)
- T0's calendar day opens at a mark **at T0**, not at CST midnight of that partial day
- Each later day opens at a mark **at 00:00 Asia/Shanghai**
- `day_low` is the minimum qualifying mark from that open through the next midnight, or through T_score on the last day
- `daily_loss = (day_open − day_low) / day_open`

`FLAT_MARK` rows without that rule are not a day low. Using them would understate the drop and would be a guess.

**Line A today:** `NOT_SCORABLE` / `NOT_SCORABLE_ON_LINE_A`.

### C8 — Profit concentration

```text
share = max(winning official nets) / sum(positive official nets)
```

**Line A today:** `NOT_SCORABLE`, same funding block as C3.  
**PASS** when the pool is positive and `share ≤ 0.25`.

### C9 — Governance incidents

Incident counts are not columns on the trade ledger. An absent register, an empty file, or a file without an `ATTEST_COVERAGE` row whose window covers `[T0, T_score]` is `NOT_SCORABLE`. It is not four zeros.

When a register is supplied, the scorer counts `INCIDENT` rows in the window for:

- `UNAUTHORIZED_PRIVILEGE`
- `UNAUTHORIZED_LIVE_ORDER`
- `LEDGER_TAMPER`
- `RISK_GATE_BYPASS`

**Line A today:** `NOT_SCORABLE` / `NOT_SCORABLE_ON_LINE_A`.  
PR #416 names future source paths and does not create the register. That PR is not on the formal scoring chain.

### C10 — Ledger integrity

Structural checks, which can FAIL today:

- every row has `prev_hash` and `row_hash`
- each later `prev_hash` equals the previous `row_hash`
- `ledger_event_id` is unique
- ids of the form `le-N` step by 1
- zero unparsed JSON lines

A break, a duplicate, a gap, or an unparsed line is **FAIL**.

Payload digest recomputation is **NOT_SCORABLE** / `PAYLOAD_HASH_ALGORITHM_NOT_IN_REPO`. The writer that canonicalizes `row_hash` is not in this GitHub checkout. A self-consistent chain does not by itself prove the payload was not rebuilt. The published C10 status therefore stays `NOT_SCORABLE` when the structure holds, with `structural_status: PASS` and `payload_digest_status: NOT_SCORABLE`.

### R0 — Random direction, pre-registered

Same counted trades. Gross is `exit.gross_pnl` when present. Otherwise it is `net_ex_funding + recorded fee and slippage` when those costs exist. Otherwise it is `side × (exit.effective_price − entry.effective_price) × entry.quantity`. `signal_price` and `reference_price` are not read for this.

A fair coin has expected gross 0. Funding that flips sign with side has expected value 0. Expected random-direction net = `− recorded costs`.

```text
PASS when official Anchor net > expected random-direction net
```

With funding present and equal to zero, that comparison is positive gross. It is weaker than C3 whenever costs are positive. It is still required, so a cost-identity error cannot hide inside the net. After §9 records a seed, the same net must also beat the median of 1000 seeded books. The seed is `SHA256(seed | sim | entry ledger_event_id)`; the low bit of the digest picks the same side or the opposite side, and funding flips with the side. Until a seed is frozen, `seeded_comparison` is `NOT_FROZEN` and the expected book is the binding comparison.

**Line A today:** `NOT_SCORABLE` / `NOT_SCORABLE_ON_LINE_A`, because the official net includes funding. `diagnostic_ex_funding` may still say whether the ex-funding book beats the expected null. That object is `not_a_score: true`.

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

The MCP summary does not return row keys. The field inventory in the gap document is the 2026-09-30 preflight of the live JSONL (41 keys, no stop, no `equity_at_open`, no `risk_amount`, funding null). This environment did not re-dump the 1666-row file. The scorer uses only keys present on the copy it is given.

---

## 8. Recommendations (not applied)

These do **not** change the thresholds in §0.

1. Keep C3's requirement that funding be present. Do not adopt "ex-funding counts as the official net." That would lower the exam. Today's honest status is `NOT_SCORABLE`, not a zero.
2. Keep 0.5%, 8%, 2%, 25%, 90 days, 50 trades, and profit factor 1.10. The pre-T0 cumulative figure is negative and is not a reason to move any bar.
3. Keep the V1 no-loss special case for C4, and keep it conjunctive with C1 and C2.
4. Before freeze, vendor the writer's `row_hash` canonicalization into this repository so C10's payload check can become a real PASS/FAIL. Until then, leave payload recomputation `NOT_SCORABLE`.
5. Add a pre-registered block-bootstrap report on the post-T0 official nets. Publish it beside the grade. Do not turn it into a new numeric gate in this draft.
6. For R0, consider also requiring Anchor's official net to beat the 95th percentile of the seeded random books, not only the expected book and the median. Not applied. The binding comparison remains the one in §5.
7. Do not loosen C7's 2% because sparse `FLAT_MARK` rows miss the intraday low. Leave C7 unscorable until `MARK_RULE_C7_V1` marks exist.
8. Do not alias `OPEN.net_liquidation_equity` to `equity_at_open`. The readiness note called that a proxy. This draft refuses the alias.

---

## 9. Freeze signature (blank on purpose)

I freeze **PROJECT ANCHOR OFFICIAL EVALUATION PASS LINE V1.1** as the sole bar for requesting a minimal-capital live Pilot, until a numbered successor is frozen. Scoring starts at T0. Only trades whose signal (when recorded), entry, and close are all inside `[T0, T_score]` count. Line A rows are not rewritten. Line B, if opened later, starts at its own T_alloc and its own files. Passing does not authorize live trading.

| Field | Value |
|-------|--------|
| Freeze time T0 (Asia/Shanghai) | ____________________ |
| T_alloc for any new capital-allocation rule | ____________________ (blank if none) |
| Founder name | ____________________ |
| Signature / mark | ____________________ |
| Document SHA-256 (**required at freeze**) | ____________________ |
| Git commit SHA of this frozen file (**required at freeze**) | ____________________ |
| R0 random-direction seed (**required at freeze if seeded median is in force**) | ____________________ |
| `T0_FROZEN` | `NO` until this table is filled and the hash is committed |

The scorer's `frozen` field stays `false`. Filling this table in a later commit is the freeze. This draft does not fill it.

---

## 10. How to run the scorer

From a checkout of this repository, against a **copy** of the JSONL. Do not point it at the StateDirectory (`affl-v2-official-ledger`, `anchor-official-ledger`, or `/var/lib/private`). Those paths are refused. The input is opened read-only. `--out` cannot be the ledger path.

```bash
cd /path/to/project-anchor
python3 scripts/score_official_fake_fill_pass_line.py \
  --ledger /path/to/copy/anchor_fake_fill_ledger_v2_official.jsonl \
  --t0 'YYYY-MM-DDTHH:MM:SS+08:00' \
  --t-score 'YYYY-MM-DDTHH:MM:SS+08:00' \
  --governance /path/to/copy/governance.jsonl \
  --random-seed '<seed recorded in section 9>' \
  --out /path/to/score-report.json
```

Omit `--t0` and `--t-score` before freeze. The report will mark the windowed criteria `T0_NOT_FROZEN`. Exit status 0 means a report was written. The grade is the JSON field `overall`. Exit status 2 means the path was refused or a timestamp did not parse.

Tests:

```bash
cd /path/to/project-anchor
python3 -m unittest tests.test_score_official_fake_fill_pass_line
```

---

## 11. Repo facts that bear on these constraints

Checked in this checkout and against open PRs #416 and #417. None of these facts were "fixed" by rewriting a ledger.

| Fact | Relation to this draft |
|------|------------------------|
| V1 R2 text uses profit factor > 1.10. A short summary of that draft still said expectancy > 0. | This draft follows R2. |
| V1 says a missing required field fails eligibility. | The scorer emits `NOT_SCORABLE` and `overall = NOT_ELIGIBLE`. It does not print a fake measured FAIL. |
| Readiness note G1 said a missing stop makes C6 fail, and called `OPEN.net_liquidation_equity` a proxy for `equity_at_open`. | C6 is `NOT_SCORABLE_ON_LINE_A`. The proxy is not accepted. |
| PR #416 is open and states `FORMAL_SCORING_CHAIN=NOT_ON_FORMAL_SCORING_CHAIN`, `OFFICIAL_SIGN_LOCK=NO`, and missing funding stays `EX_FUNDING`. | Funding is still `MISSING` for Line A. That PR does not close C3, C7, or C9. |
| PR #417 is open, `DEPLOY=NO`, new `strategy_version`, and it does not load a prior Official ledger. | That is Line B material. It is not merged and must not be backfilled onto Line A. |
| `affl_v2` writer code is not in this GitHub repository. | The hash recipe and the fee formula are taken from the preflight and from the ledger's own per-exit note, not from a local engine import. |
| Legacy equity CSV header is 6 columns and the body is 10. | The scorer does not read that CSV. |
| `docs/GO_LIVE_CHECKLIST.md` records live trading **NO-GO**. The live MCP status on 2026-10-22 also reports `live_trading: NO-GO` and `go_live: NO-GO`. | Consistent with this draft. A pass line PASS would still not authorize orders. |
| MCP `net_pnl_note` says per-exit NET_PNL excludes entry costs. | The C3 formula subtracts entry `fee_paid` and entry `slippage_cost`. |
| No file in this checkout contains a count of 249 missing-candle events. | The retention rule is still in the scorer: every row is counted, including `MISSING_CANDLE`, and nothing is deleted. A unit test locks a 249-row gap set. If that count exists only on the host ledger, this PR does not touch it. |
| Open PR #426 collapses repeated `PENDING_NEXT_BAR` rows on a read-side summary. | This scorer does not collapse or drop those rows. A display collapse is not a license to rewrite the file. |

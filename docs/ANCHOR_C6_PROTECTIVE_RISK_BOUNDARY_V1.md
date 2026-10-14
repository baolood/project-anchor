# ANCHOR_C6_PROTECTIVE_RISK_BOUNDARY_V1

**Status:** Gate A design + implementation (Fake-Fill protective floor)  
**DEPLOY:** `NO`  
**Live trading:** `NO-GO`  
**Auto execution / Vultr / production runner:** not in this change  
**Exam scores:** this document records no Net PnL, profit factor, drawdown, win rate, or pass/fail grade

Gate A is the protective open path only: frozen stop, size capped by 0.5% of equity at open, immutable ex-ante ledger fields, and a real hard-stop exit. Gate B (funding ingest, equity CSV v2.1, C7 mark rule, C9 register, pass-line freeze, runner deploy) is out of scope.

The Official Fake-Fill writer described in the readiness notes (`affl-causal-successor/affl_v2` engine on the Mac tree) is not in this GitHub checkout. This change adds that package’s Gate A boundary here. It does not attach itself to a host runner and it does not read an Official ledger to choose parameters.

---

## 1. Precommitted rules

These rules are part of the versioned contract `official_ledger_c6_v1`. They are constants in code. Revising any of them requires a new `strategy_version` and a new `schema_version`. Old series stay on disk and are not imported.

| Constant | Value | Role |
|----------|--------|------|
| `STRATEGY_VERSION` | `affl_v2_c6_protective_v1` | New strategy series. Prior exam rows are a different series. |
| `SCHEMA_VERSION` | `official_ledger_c6_v1` | Ledger shape for this series. |
| `STOP_RULE_ID` | `STOP_RULE_C6_FIXED_ADVERSE_BPS_V1` | How `preset_stop_price` is produced. |
| `SIZE_POLICY_ID` | `SIZE_POLICY_C6_SHRINK_TO_MAX_ELSE_REJECT_V1` | What happens when requested size exceeds the budget. |
| `FIXED_ADVERSE_STOP_BPS` | `100` | Adverse price distance from the fill. One percent of price. |
| `FEE_BPS` | `5` | Fake-Fill fee schedule, both legs. |
| `SLIPPAGE_BPS` | `2` | Fake-Fill simulated slippage, adverse. |
| `MAX_RISK_PCT` | `0.005` | Hard cap: 0.5% of `equity_at_open`. |
| `QTY_QUANTUM` | `1e-8` | Quantity step. Size is rounded down, never up. |

`SIZE_POLICY_C6_SHRINK_TO_MAX_ELSE_REJECT_V1` is the advance choice between shrink and reject:

1. The stop is fixed first.
2. Maximum quantity is solved from that stop, the fee schedule, and simulated slippage.
3. If the candidate quantity is above that maximum, the fill quantity **shrinks** to the maximum. The stop is left where the rule put it.
4. If the maximum quantity rounds to zero, or the post-round risk is still above 0.5%, the open is **rejected** (`NO_FILL`). No position is created.
5. A candidate that already fits is filled at that candidate size (floored to the quantum).

There is no second policy that keeps an oversized quantity, and no policy that moves the stop farther away so a desired size fits.

The basis points above are round version constants. They were not selected from Official Net PnL, profit factor, or drawdown. This module has no input for those series.

---

## 2. How the stop is produced

Order, for every OPEN candidate (`LONG` or `SHORT`):

1. The model’s signal supplies the side, a positive reference price, and a candidate size. It does not supply the stop.
2. Fake-Fill entry price (adverse slippage already in the fill):

```text
slip_rate = SLIPPAGE_BPS / 10000
LONG  entry_price = reference_price * (1 + slip_rate)
SHORT entry_price = reference_price * (1 - slip_rate)
```

3. Frozen stop, from that entry price only:

```text
stop_rate = FIXED_ADVERSE_STOP_BPS / 10000
LONG  preset_stop_price = entry_price * (1 - stop_rate)
SHORT preset_stop_price = entry_price * (1 + stop_rate)
stop_distance       = abs(entry_price - preset_stop_price)
```

`frozen_stop_price(side, entry_price)` takes side and entry price. A suggested stop, a wider stop, or an outcome series is not an argument. Calls that try to pass one raise `TypeError`.

The stop is on the protective side of the entry: below entry for LONG, above entry for SHORT. A zero or non-positive distance is not a stop; the open is rejected and no stop number is invented for a non-positive reference price.

---

## 3. How size is constrained by 0.5%

After the stop exists:

```text
equity_at_open   = net liquidation immediately before this open
max_risk_amount  = equity_at_open * 0.005

fee_rate         = FEE_BPS / 10000
entry_slip_u     = abs(entry_price - reference_price)
exit_slip_u      = preset_stop_price * slip_rate
fee_u            = (entry_price + preset_stop_price) * fee_rate

per_unit         = stop_distance + entry_slip_u + exit_slip_u + fee_u
max_quantity     = floor(max_risk_amount / per_unit, 1e-8)
```

`per_unit` is the ex-ante worst-case loss of one unit if the protective stop is touched:

- price loss from the fill to the preset stop
- simulated entry slippage (fill versus reference; not inside `stop_distance`)
- simulated exit slippage (cash beyond the trigger; the trigger price itself is not moved)
- expected entry fee and expected exit fee at the stop notional

```text
risk_amount(q) = per_unit * q
risk_pct(q)    = risk_amount(q) / equity_at_open
```

Filled quantity:

```text
if candidate_quantity > max_quantity:
    quantity = max_quantity          # SHRINK
else:
    quantity = floor(candidate_quantity, 1e-8)
```

Open is allowed only when `quantity > 0` and `risk_pct(quantity) <= 0.005`. Equality with 0.5% is allowed. Anything above 0.5% is not written as `OPEN`.

Worked shape (LONG, reference `100`, equity `10000`, so `max_risk_amount = 50`):

```text
entry_price       = 100.02
preset_stop_price = 99.0198
stop_distance     = 1.0002
```

`per_unit` at these inputs is `1.13952386`. `max_quantity` floors to `43.87797549`. A candidate of `1000` still opens at that quantity with stop `99.0198`. The stop is not moved down toward zero to buy room for the candidate. `risk_amount` stays at or under `50`.

---

## 4. After open: stay or tighten, never widen

`preset_stop_price`, `risk_amount`, `risk_pct`, `equity_at_open`, `entry_price`, and `trade_id` on the `OPEN` / `REVERSE_ENTRY` row are the ex-ante record. Later events do not rewrite that row.

The working trigger (`protective_stop_price`) starts equal to `preset_stop_price`.

| Proposed stop | LONG | SHORT | Result |
|---------------|------|-------|--------|
| Farther from entry than the working stop | lower than current | higher than current | `STOP_UPDATE_REJECTED`, reason `STOP_WIDEN_FORBIDDEN`. Working stop unchanged. |
| Closer to entry, still strictly protective | higher than current and below entry | lower than current and above entry | `STOP_TIGHTEN`. Working stop updates. OPEN row unchanged. |
| Equal to the working stop | | | No event. |
| Across or beyond entry | | | Rejected as widen / invalid. Working stop unchanged. |

No path tightens or widens the stop from realized results. Tighten is an explicit later instruction, not an automatic fit.

---

## 5. Ledger events (Official-shaped)

New series only. The book has no loader for a prior Official file, and it does not append onto `strategy_version` values other than `affl_v2_c6_protective_v1`.

Every row carries `schema_version`, `strategy_version`, `stop_rule_id`, `size_policy_id`, hash chain (`prev_hash`, `row_hash`), and `ledger_event_id`.

Funding is not invented. Rows keep `funding_pnl = null`, `FUNDING_DATA_STATUS = MISSING`, `NET_PNL_STATUS = EX_FUNDING`.

### Identifiers

```text
trade_id = "tr_" + entry ledger_event_id
```

`OPEN` and `REVERSE_ENTRY` mint `trade_id`. `FLAT_EXIT`, `REVERSE_EXIT`, and `HARD_STOP_EXIT` copy it. A `REVERSE_ENTRY` mints a new id for the new leg. A `NO_FILL` does not mint a `trade_id`.

### Event types

| `event_type` | When | Fill |
|--------------|------|------|
| `OPEN` | Flat book, `LONG` or `SHORT`, size fits under the cap (possibly after shrink) | `FILLED` |
| `NO_FILL` | Non-positive reference, non-positive candidate, or no positive quantity inside the cap | `NO_FILL` |
| `FLAT_EXIT` | Open leg, signal `FLAT` | `FILLED` at the signal’s adverse fill |
| `REVERSE_EXIT` | Open leg, opposite signal | `FILLED` at the signal’s adverse fill |
| `REVERSE_ENTRY` | Immediately after `REVERSE_EXIT`, new leg passes the same gate | `FILLED` |
| `HARD_STOP_EXIT` | Mark touches or gaps through the working stop | `FILLED` |
| `STOP_TIGHTEN` | Explicit tighter stop accepted | not a fill |
| `STOP_UPDATE_REJECTED` | Explicit wider stop refused | not a fill |

### Ex-ante fields on `OPEN` and `REVERSE_ENTRY`

Written before the row is appended, and stored on the leg for later exits:

| Field | Meaning |
|-------|---------|
| `trade_id` | Stable open→close id |
| `entry_price` | Adverse Fake-Fill price |
| `preset_stop_price` | Frozen stop from §2 |
| `equity_at_open` | Equity immediately before the fill |
| `risk_amount` | `per_unit * quantity` |
| `risk_pct` | `risk_amount / equity_at_open` |
| `stop_distance` | `abs(entry_price - preset_stop_price)` |
| `max_risk_amount` | `equity_at_open * 0.005` |
| `max_quantity` | Largest quantum quantity inside the cap |
| `candidate_quantity` | Requested size |
| `quantity` | Filled size |
| `size_action` | `UNCHANGED` or `SHRINK` |

Exit rows copy those ex-ante values from the leg. They do not recompute them from the exit price.

### Hard stop

While a leg is open, a mark at `price`:

```text
LONG  triggers when price <= protective_stop_price
SHORT triggers when price >= protective_stop_price
```

Exit fill is the worse of the mark and the slippage-adjusted trigger (a gap through the stop fills at least as badly as the slipped trigger). `reason_code = HARD_STOP_TOUCHED`. The OPEN row’s `preset_stop_price` stays the original trigger even when the fill gaps beyond it.

A mark that has not touched the working stop does not exit.

### Signal exits

`FLAT` closes the leg with `FLAT_EXIT`. The opposite side closes with `REVERSE_EXIT` and then runs the open gate for `REVERSE_ENTRY`. Those exits use the signal reference and the slippage schedule. They do not wait for the stop, and they do not move it.

A same-side signal while a leg is open does not add size and does not move the stop.

`execution` other than `fake_fill` raises `LIVE_TRADING_NO_GO` and writes nothing.

---

## 6. Caller boundary

`position` is a read-only snapshot. Assigning its fields, or replacing `book.position`, does not change the working stop or the ex-ante values copied onto later exits. The working stop moves only through `propose_stop_update`.

Reference prices, marks, and exit prices must be finite and strictly positive before any cash or position change. Zero, negative, NaN, and Infinity do not create a filled exit.

`observation_id` and `at` must be non-empty plain strings, not mutable containers. The ledger row and caller return value are detached copies prepared before cash, position, or the event list change. Copy or hash failures leave the book unchanged; an append failure restores cash, position, stop, sequence, hash head, and event count. This is an in-memory event commit boundary, not durable storage or whole-reversal transaction support.

## 7. What this change does not do

- Deploy, restart, or reconfigure Vultr, launchd, nginx, or a ledger poller
- Authorize live orders, testnet sends, or production execution
- Read Official ledger PnL, profit factor, or drawdown to set the stop or the size policy
- Import, replay, or score an older strategy/schema series
- Invent funding, rewrite the legacy equity CSV, add the C7 mark rule, or open a C9 register
- Move the stop away from entry so a requested size passes the 0.5% cap

---

## 8. How to verify

From the repository root:

```bash
cd /path/to/project-anchor
python3 -m unittest tests.test_c6_protective_risk_boundary
```

The tests cover: stop formula independent of outcome inputs; shrink when the candidate exceeds 0.5%; reject when no positive size fits; OPEN ex-ante fields; stop widen refused and tighten accepted without rewriting OPEN; `HARD_STOP_EXIT`; `FLAT_EXIT` and `REVERSE_EXIT` / `REVERSE_ENTRY`; live execution refused.

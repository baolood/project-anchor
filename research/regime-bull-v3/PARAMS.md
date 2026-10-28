# REGIME_BULL_LEV15_V3 — forward paper-shadow test, max 1.5x leverage + hard drawdown brake (pre-registered)

Frozen BEFORE any V3 forward row exists. Paper only: no real money, no exchange keys, no orders, no host changes.
Related: V1 (`../regime-bull/`), V2 forward shadow (`../regime-bull-v2/`, unchanged by V3), leverage what-if (`../regime-bull/leverage_whatif/`).

## Honest status of the evidence
The historical leverage what-if (1x/1.5x/2x/3x on 2018–2026 BTC and ETH) has been **seen** by the founder and by the author before this file was written, and it motivated the 1.5x + brake idea.
Any historical number for these rules is therefore **contaminated and is NOT evidence**. A frozen-rules history run will be produced only as `INFO_HISTORY.md`, labelled information only. The only evidence for V3 is forward data after the freeze.

## Instrument and data
- BTCUSDT daily klines, Binance public market data: primary `https://data-api.binance.vision/api/v3/klines` (mirror of api.binance.com, which is geo-blocked from the box); fallback `data.binance.vision` zips. Closed candles only (close time already in the past, 00:00 UTC grid). Fields used: close and low.
- `date` in the ledger = UTC open date of the candle. A row dated D is decided and executed at the close of that candle (D+1 00:00 UTC) and earns day D+1's return.
- Perp mechanics are modelled on BTCUSDT; no real perp account exists.

## Execution timing (same as V2)
Signal and sizing computed from closes up to and including day t, executed at day t's close; the position then earns day t+1's close-to-close return.

## Rules — primary line V3 (long-only, max 1.5x exposure)
Let C(t) = close of day t. Exactly V2 variant (b) for the signal and the sized weight:
- SMA200(t) = mean of C(t-199..t). Regime ON iff C(t) > SMA200(t) (strict).
- σ(t) = sample stdev (ddof=1) of the 60 daily log returns ln(C(s)/C(s-1)), s = t-59..t, × √365.
- sized(t) = min(1.0, 0.40 / σ(t)); this is V2(b)'s unlevered weight.
- **Target exposure X(t) = 1.5 × sized(t)** (notional ÷ equity), so 0 ≤ X ≤ 1.5. Long only.
- Carried exposure x_cur = notional ÷ equity at the close after the day's price move and funding (it drifts with price).
- Decision at close t, when the brake is OFF: regime OFF → target 0. Regime ON: if x_cur = 0 → X(t); else if x_cur > 1.5 → X(t) (cap enforced); else if |X(t) − x_cur| ≥ 0.10 → X(t) (0.10 band, in exposure units); else keep (no trade).
- Turnover(t) = |notional_new − notional_old| ÷ equity (notional_new = target × equity before the trade cost). Cost = 0.0015 × turnover (15 bp per side = 10 bp fee + 5 bp slippage), deducted from equity at the trade.
- Daily P&L: equity += notional × r(t+1) − notional × funding(t+1); notional then drifts by (1 + r(t+1)).

## Funding (long pays when the rate is positive; negative = received)
- Rate for UTC day D = sum of the three 8-hour settlements dated D (00:00, 08:00, 16:00 UTC). Charged on the carried notional for the whole day.
- Source 1, preferred: Binance USDT-M perpetual BTCUSDT fundingRate, public archive `data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/` (published after each month ends; `fapi.binance.com` is geo-blocked from the box and there is no daily archive).
- Fallback 2, for days Binance has not yet published: OKX public `BTC-USDT-SWAP` funding history (`/api/v5/public/funding-rate-history`, realized rate), same 8-hour grid, used as a stated proxy for Binance's rate. Row tagged `okx_proxy`.
- Fallback 3, if neither is available: assumed 0.01% per 8h = 0.03% per day. Row tagged `assumed`.
- The funding value used is stored in each ledger row and never rewritten. At each checkpoint an information-only true-up replays V3 with Binance actual funding once published; if the true-up would flip any pass-bar criterion, the report says so and shows both.

## Liquidation check (daily low)
For day D with carried exposure x (> 0) and move m = low(D) ÷ C(D-1) − 1 (low versus the previous close, i.e. the rebalance level): liquidated if 1 + x·m − 0.005·x·(1+m) ≤ 0 (equity at the low ≤ 0.5% maintenance margin of the notional at the low).
On liquidation equity goes to 0, exposure 0, the shadow is dead (every later row stays at 0) and the verdict is FAIL. No liquidation fee is modelled (equity is already ~0).

## Hard drawdown brake (fixed now)
- Running peak P of V3 equity, measured at closes, starting at the starting equity 10,000. Brake threshold: equity ≤ 0.80 × P.
- **Close check**: if equity at the close ≤ 0.8·P → brake ON, sell all exposure at that close (cost 15 bp of notional).
- **Intraday check**: if the day's low would take equity to ≤ 0.8·P (equity at the low = E·(1 + x·m)), brake ON during that day: exposure goes to 0 immediately. Conservative daily-bar fill: the exit is assumed at the worse of (the price where equity = 0.8·P) and the day's close, with 15 bp of notional cost; funding for that day is still charged on the carried notional.
- While the brake is ON the line stays flat. It re-enters only on a fresh ON signal: after the trigger the regime must be seen OFF at at least one later close, and then ON at a later close. For a close-triggered brake, the trigger close itself is not counted; for an intraday-triggered brake, that day's close counts.
- On re-entry: position = X(t) (the sized weight × 1.5), the peak P is reset to the current equity, the brake turns OFF.
- Reporting drawdown (`dd_*` columns, used by the pass bar) uses a separate never-reset running peak of equity at closes (start 10,000).

## Benchmarks (tracked, not judged except as stated in the bar)
- **V2(b) 1x, no brake**: exactly V2's variant (b) rules (see `../regime-bull-v2/PARAMS.md`), spot-style with no funding, 15 bp per side — its equity should equal V2's ledger `equity_b`. This is the Calmar comparator in the bar.
- V2(b) 1x with funding charged as if held via the perp (informational, column `eq_b1f`).
- BTC buy-and-hold: enters at the first decision close (15 bp once), no exit cost, no funding.
- Unjudged benchmarks: `eq_b1f`. The brake events and the 45 bp stress are information only.

## Start and clock
- Starting paper equity 10,000 for every line; all lines start flat and the first decision trades at its close.
- First forward row = the latest closed daily candle at the moment of initialisation (same as V2: the candle opened 2026-10-26 00:00 UTC, closed 2026-10-27 00:00 UTC). Earlier closes are lookback only.
- Checkpoints: 6 months = 2027-04-27 (interim), 12 months = 2027-10-27 (judged). Ledger is append-only; a late runner appends missing closed days in order.

## Pre-registered pass bar (forward data only; V3 line only)
Phase definitions as in V2: ex-post 20% zig-zag on forward BTC closes from the first ledger date; bull phase = up-leg ≥ +50% trough-to-peak (an unfinished leg counts if already ≥ +50%); bear phase = down-leg ≥ 30% peak-to-trough.
- **L0 No liquidation**: any liquidation (at any time) = FAIL.
- **L1 Survive**: V3 max drawdown at the close (reporting peak) no worse than −30%.
- **L2 Worth the leverage**: V3 Calmar ≥ V2(b) 1x Calmar AND ≥ BTC buy-and-hold Calmar, over the same window (Calmar = CAGR ÷ |max DD at close|, CAGR = (E_end/E_start)^(365/days) − 1; if a comparator's drawdown is 0, its Calmar counts as +∞ when CAGR > 0, so a comparator with zero drawdown cannot be beaten).
- **Cycle test**: INSUFFICIENT unless the window contains BOTH at least one bull phase AND at least one bear phase (or buy-and-hold max drawdown ≤ −30%) as defined above.
- **Verdicts**: at any time FAIL if L0 is breached or the −30% line at the close is breached. 6 months = interim, reported as "so far" (never a PASS). 12 months: PASS only if cycle test satisfied and L0, L1, L2 all hold; FAIL if the cycle test is satisfied and any fails; otherwise INSUFFICIENT (then the shadow keeps running unchanged and is re-checked every further 6 months; the founder decides whether to stop).
- Not part of the bar: random-timing tests (V1 C4), the number of brake triggers (reported only).

## Honest limits
- 6–12 months is shorter than a BTC cycle; INSUFFICIENT is the expected outcome unless a real bear and a real bull both occur.
- Daily bars: the brake and liquidation are approximated from the daily low and close; true intraday order, mark-price wicks, auto-deleveraging, outages are not modelled.
- Funding for recent days is a proxy (OKX) or an assumption until Binance publishes; the true-up is informational.
- Paper fills at the daily close with a flat 15 bp.
- No rule, cost, band, brake level, start date or bar will change after this freeze; a different idea is a new family.

## Daily command
`python3 /workspace/anchor-redesign/regime-bull-v3/paper_track.py`  (idempotent; appends only newly closed days to `ledger.csv`; exit 2 on data errors, 3 on ledger/replay mismatch, nothing written in either case)

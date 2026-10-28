# REGIME_BULL_SURVIVE_V2 — forward paper-shadow test (pre-registered)

Frozen BEFORE any forward data is recorded. No ledger row exists at the time of writing. Paper only: no real money, no exchange keys, no orders of any kind.
Parent study: REGIME_BULL_SURVIVE_V1 (`../regime-bull/REPORT.md`, PARAMS sha256 92e019a0…8ef0, verdict FAIL for the selected variant (c)).
Why V2: V1 had no fresh history left to test on. Variant (b) is the one the founder wants to watch live-forward; nothing is re-tuned. V2 has no new alpha claim.

## Instrument and data
- BTCUSDT spot daily klines, Binance public market data. Primary endpoint `https://data-api.binance.vision/api/v3/klines` (public market-data mirror of api.binance.com, which is geo-blocked from the box);
  fallback `https://data.binance.vision` (daily/monthly zips). `api.binance.com` is also accepted if reachable.
- Closed candles only: a candle counts only when its close time (open 00:00 UTC + 24h) is already in the past. The still-forming candle is never used.
- `date` in the ledger = the UTC open date of the candle. A row dated D is decided and executed at the close of that candle, i.e. at D+1 00:00 UTC.
- BTCUSDT is a USD proxy. Costs are modelled, fills are not real.

## Execution model (differs only in labelling from V1)
Signal is computed from closes up to and including day t, and executed at day t's close. The position then earns day t+1's close-to-close return.
(V1 used signal on close(t-1) and trade at open(t); open(t) ≈ close(t-1) on 24h bars, so this is the same thing.)

## Rules — primary line, variant (b) SMA200_VOLTARGET, copied from V1
Let C(t) = close of day t.
- SMA200(t) = mean of C(t-199..t) (200 closes, including day t). Regime ON iff C(t) > SMA200(t) (strictly greater).
- σ(t) = sample standard deviation (ddof=1) of the 60 daily log returns ln(C(s)/C(s-1)), s = t-59..t, multiplied by √365.
- sized(t) = min(1.0, 0.40 / σ(t)). Target vol 0.40, cap (max weight) 1.0, long only, no shorts, no leverage above 1x.
- cur(t) = the weight carried into the close of day t after drifting with day t's return r(t) = C(t)/C(t-1) − 1: cur = w_prev·(1+r)/(1+w_prev·r) (0 if w_prev = 0).
- New weight w(t): if regime OFF → 0. If regime ON: if cur = 0 → sized(t); else if |sized(t) − cur| ≥ 0.10 → sized(t); else cur (no trade).
- Turnover(t) = |w(t) − cur(t)|. Cost = 0.0015 × turnover (15 bp per side = 10 bp fee + 5 bp slippage), charged on equity at the trade.
- Equity(t) = Equity(t-1) × (1 + w_prev·r(t)) × (1 − 0.0015·turnover(t)).

## Rules — secondary line, variant (a) SMA200 (labelled SECONDARY; shown, never judged)
Weight 1 if regime ON (C(t) > SMA200(t)), else 0. Same costs, same execution, same drift handling.

## Benchmark — BTC buy-and-hold from the same start
Buys at the first decision close (15 bp entry charged once), holds, no exit cost.

## Starting state and clock
- Starting paper equity 10,000 for all three lines (b, a, buy-and-hold).
- Forward start date 2026-10-27 (Asia/Shanghai). The first decision is the latest closed daily candle at that moment: the candle opened 2026-10-26 00:00 UTC (closed 2026-10-27 00:00 UTC = 08:00 Asia/Shanghai).
  The first ledger row is that candle. No earlier day is ever in the ledger; earlier closes are used only as lookback for SMA200 and σ. The three lines start flat at 10,000 before that first decision; the first decision trades at its close.
- Drawdown = equity / running peak of equity − 1, with the peak starting at the starting 10,000.
- Checkpoints: 6 months = 2027-04-27, 12 months = 2027-10-27. Evaluation is on the ledger rows up to that date; the ledger is append-only.
- Ledger rows are never rewritten or deleted. A runner that misses days must catch up by appending the missing closed days in order (each row records when it was written).

## Pre-registered pass bar (forward data only, vs BTC buy-and-hold from the same start; judged on the primary line (b) only)
- **F1 Survive**: forward max drawdown of (b) no worse than −35% AND shallower (smaller in magnitude) than buy-and-hold's.
- **F2 Bull capture**: if a bull phase occurs in the window, aggregate bull capture ≥ 50%.
- **F3 (12-month checkpoint only)**: Calmar of (b) ≥ buy-and-hold's Calmar, OR CAGR of (b) ≥ 70% of buy-and-hold's CAGR. Calmar = CAGR ÷ |max drawdown|; CAGR = (E_end/E_start)^(365/days) − 1.
- Phase definitions (ex-post, scoring only, computed on forward BTC closes from the first ledger date): 20% zig-zag turning points. Bull phase = confirmed up-leg (or unfinished leg already) with trough-to-peak gain ≥ +50%.
  Bear phase = down-leg with peak-to-trough drop ≥ 30%. Bull capture = Σ ln(1+r_strategy) ÷ Σ ln(1+r_buy&hold) over the bull-phase days (the days after the trough date through the peak date).
- The random-timing test (V1 C4) is not part of this bar. This is stated openly: V1 showed variant (b) did not clear that bar out-of-sample on BTC (87th percentile of the null, p95 required). Passing V2 therefore does not prove timing skill.

## Verdicts and the "insufficient" rule
Possible verdicts: PASS, FAIL, INSUFFICIENT.
- **FAIL at any time**: (b)'s forward max drawdown is worse than −35%. (A breach is a fact regardless of how the cycle looks.)
- **Cycle test**: the window is informative only if it contains BOTH (i) at least one bear phase as defined above, or buy-and-hold max drawdown ≤ −30%, AND (ii) at least one bull phase as defined above.
- **Interim (6 months)**: reported only as "so far" — FAIL if the −35% line was breached, otherwise INSUFFICIENT or "on track" (F1/F2 holding with no breach). It is not a PASS and does not change anything.
- **12 months**: PASS only if the cycle test is satisfied AND F1, F2 and F3 all hold. FAIL if the cycle test is satisfied and any of them fails, or the −35% line was breached. If the cycle test is NOT satisfied the verdict is **INSUFFICIENT**, not PASS, even if every number looks good.
  A window with no full cycle cannot prove "survive bears, earn in bulls". On INSUFFICIENT the shadow keeps running unchanged and is re-checked every further 6 months; the user decides whether to stop it.
- If buy-and-hold's max drawdown is shallower than −20%, the "better than buy-and-hold" half of F1 is not informative (no real bear) and F1 counts as not tested.
- Variant (a) and the 45 bp stress are reported for information only and cannot change the verdict.

## Honest limits
- 6–12 months is shorter than one BTC cycle. Expect INSUFFICIENT unless a real bear and a real bull both fall inside the window.
- Paper fills at the daily close with a fixed 15 bp; real fills, outages, API/key issues and exchange rules (e.g. Kraken account limits) are not tested.
- Daily-close marks hide intraday drawdowns.
- No parameter, rule, cost, start date or pass bar will be changed after this freeze. A different idea is a new family with new PARAMS.

## Daily command
`python3 /workspace/anchor-redesign/regime-bull-v2/paper_track.py`  (idempotent; appends only newly closed days to `ledger.csv`; exits non-zero on data errors without writing)

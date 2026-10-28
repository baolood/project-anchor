# REGIME_BULL_VOLTARGET_V1 — pre-registered historical test of volatility-targeted sizing

Written 2026-10-27 (Asia/Shanghai) BEFORE the new rule was run on any data. No equity curve, return, drawdown or Calmar of this rule exists at the time of locking.
Only the following were looked at to write this file: file listings, row counts / gaps / non-positive prices of the new data, the public price-derived zig-zag leg list of the judged window (V1 phase definition, price only), and median daily dollar volume per year of the data.
Paper/backtest only: no real money, no exchange keys, no orders, no host changes. V1, V2, V3, Line A, the legacy equity CSV, the governance register and the PASS LINE freeze are untouched.
Family goal (user's): "bull-market participation + bear-market survival", judged against BTC buy-and-hold on return AND max drawdown. NOT an all-weather-alpha claim. A FAIL is a fully acceptable outcome and will be published like the others.

## What is new (and what is not)
- Not new: SMA200 regime filter, 60-day vol estimate, 0.10 rebalance band, 15 bp/side cost, V3's 20% equity brake and daily-low liquidation check, V3's 1.5x leverage cap. All copied from V2/V3 unchanged (engine verified equal to `regime-bull-v3/paper_track.py::simulate` to 0.0 relative difference on synthetic data, see Selftest).
- New: exposure is `X(t) = min(1.5, 0.60 / σ(t))`. V2(b) is `min(1.0, 0.40 / σ)` (never above 1x) and V3 is `1.5 × min(1.0, 0.40/σ)` (a fixed 1.5x multiple of V2(b)). The new rule is a true constant-risk sizing: it scales UP above 1x when realized vol is below the target (down to σ = 0.40 → 1.5x) and DOWN when vol is high (σ = 1.2 → 0.5x).
- Why not target 0.40: with cap 1.5 it would be V2(b) with an almost never-active upward leg (needs σ ≤ 0.267) = no new idea.

## Honest status of the evidence (read before trusting any PASS)
1. Everything on Binance BTCUSDT 2017-08-17..2026-09-30 is CONTAMINATED for this family: V1 (variant b = 0.40/60d/SMA200), V2/V3 designs, the leverage what-if and V3's INFO_HISTORY were all seen, and the author saw V3's INFO_HISTORY headline numbers (V3 CAGR 10.2%, max DD −57.7%, 769 brake-ON days) before writing this file. That window is therefore NOT evidence for the new rule. It is run as INFORMATION and as a one-way VETO only (see Veto).
2. The target 0.60 and the choice to remove the 1.0 cap are motivated by knowing that V1(b)/V2 captured little of the bull markets. That knowledge comes from the Binance era only. This is the reason the judged window is a different, earlier dataset.
3. The judged window (PRE) is Bitstamp BTCUSD 2013-01-01 → 2017-08-16: not used by any Anchor strategy test. The only earlier use of this series was the unrelated random-entry study (buy-and-hold per calendar year and random-entry returns) and the price-only leg list above. BTC's 2013–2017 history is public knowledge and is known to the author in outline (2013 and late-2013 spikes, 2014–15 bear); the test is "unseen for this rule", not "unknowable".
4. 2013 contains one ×22 leg and one ×10 leg. Aggregate bull capture (log-return ratio) is dominated by those two legs; per-leg capture is reported alongside, and criterion C2 is read together with it (see C2).
5. One related family (V1, 4 variants) has already been tested on the Binance era and FAILED. This is one new variant on a different dataset. Passing it is "worth a forward shadow", never "proven".

## Data (fixed, hashed)
- PRE (judged): Bitstamp public OHLC API BTCUSD daily bars (UTC 00:00), 2011-09-13 → 2017-08-16, saved by `fetch_pre.py` (sha256 d8b95187…ee2e) to `data/bitstamp_btcusd_daily_pre2017-08-17.csv` (sha256 272ba38c…0b8c). 2,165 rows, 0 missing days, 0 non-positive prices, 0 low>close; 959 overlapping days (2015-01-01..2017-08-16) are identical to `random-baseline-study/data_btc_bitstamp_daily.csv`. 21 zero-volume days exist (18 in 2011, 3 in 2015) and are kept (price is carried by the exchange); noted as a limitation.
- Lookback: the engine needs 200 closes (SMA) and 60 returns; the judged window starts 2013-01-01 so all lookback comes from 2011-09-13 onwards. No data before the first decision is traded.
- INFO: Binance spot BTCUSDT 1d klines, the same monthly zips as V1 (`../regime-bull/data/`), 2017-08-17 → 2026-09-30, daily low from the same files. Decision window 2018-03-04 → 2026-09-30 (first day with 200 closes), same as V3's INFO_HISTORY.
- Integrity gate: if either dataset has a missing day, non-positive price or low>close, the run STOPS and reports (no result). Closes are used as USD proxies; BTCUSD (Bitstamp) and BTCUSDT (Binance) are not spliced — windows are separate.
- Why the judged window starts 2013-01-01 and not 2012-03-30 (first tradable day): Bitstamp median daily dollar volume was about $219 in 2011 and $7,067 in 2012, versus $1.05M in 2013, $5.1M in 2014, $3.1M in 2015, $2.4M in 2016. In 2012 any cost model of 15 bp is fiction. The rule was fixed by the volume table above, not by any strategy result. 2012-03-30..2012-12-31 (277 days) is not used.

## Rules — line NEW (long only, perp-style, max 1.5x)
Timing, brake and bookkeeping are those of V3 (`regime-bull-v3/PARAMS.md`); only X(t) differs. Let C(t) = close of day t, signals use closes up to and including day t; trade at the close of day t; the position then earns day t+1's close-to-close return.
- SMA200(t) = mean(C(t−199..t)). Regime ON iff C(t) > SMA200(t) (strict).
- σ(t) = sample stdev (ddof=1) of the 60 daily log returns ln(C(s)/C(s−1)), s = t−59..t, × √365. ONE lookback (60 days, same as V1/V2/V3), ONE target (0.60), neither tuned.
- Target vol 0.60 justification (a priori, stated before any run): BTC's long-run annualized realized volatility is widely quoted in the 60–80% range, so 0.60 means "average exposure about 1x when vol is typical, less than 1x when vol is above typical, up to the V3 1.5x cap when vol is calm". It is a round number, not selected from a grid; no other target is tested in this family. (If this fails, a different target is NOT tried; that would be a new family.)
- Target exposure X(t) = min(1.5, 0.60 / σ(t)) (notional ÷ equity). If σ = 0 the target is 1.5 (never occurs in the data; engine guard only).
- Carried exposure x_cur = notional ÷ equity after day t's price move and funding. Decision at close t with the brake OFF: regime OFF → target 0; regime ON: x_cur = 0 → X(t); x_cur > 1.5 → X(t); |X(t) − x_cur| ≥ 0.10 → X(t); else keep (no trade).
- Costs: 15 bp per side of traded notional (10 bp fee + 5 bp slippage), deducted from equity at the trade, charged on notional change (target × equity before cost, as V3). Stress (information only): 45 bp per side.
- Funding: assumed 0.03% of carried notional per day (0.01% per 8h, longs pay), charged every day on the whole carried notional, in both windows. There is no real perp funding series in 2013–2017 and V3's own fallback is the same figure; for the Binance window real funding exists only from 2020, so the same flat assumption is used for one convention. It is conservative against a spot-style comparator (V2 lines and buy-and-hold pay no funding) — this is deliberate and stated.
- Liquidation check on the daily low (V3): with x carried and m = low(t)/C(t−1) − 1, liquidated if 1 + x·m − 0.005·x·(1+m) ≤ 0. Liquidation sets equity to 0, ends the line (verdict criterion C0 fails).
- Hard drawdown brake (V3, unchanged): peak P of NEW equity at closes since the start/last re-entry; brake ON if close equity ≤ 0.80·P (sell all at that close, 15 bp) or if the day's low takes equity to ≤ 0.80·P (exit at the worse of the 0.80·P level and the close, 15 bp). While ON the line is flat; re-entry only after the regime is seen OFF at ≥1 later close and then ON (for a close-triggered brake the trigger close is not counted); on re-entry, position = X(t), P := current equity. Reporting drawdown uses a never-reset peak of close equity starting at 10,000.
- Starting equity 10,000, start flat; the first decision trades at its close.

## Comparators (same window, same data, same decision timing and 15 bp cost)
- BH: BTC buy-and-hold, enters at the first decision close (15 bp once), no exit cost, no funding.
- V2b: V2 variant (b) exactly (`min(1, 0.40/σ)`, SMA200, 0.10 band, spot-style, no funding, no brake). V2's primary line.
- V2a: V2 variant (a) exactly (weight 1 if C(t) > SMA200(t) else 0, spot-style). The plain "price vs 200-day line" rule. V2's secondary line; here it is also judged (stricter than V3's bar).
- NEW_NOBRAKE (information only, not judged): NEW without the brake, to show what the brake costs or saves.

## Samples and sizes
- PRE judged window: 2013-01-01 → 2017-08-16 = 1,689 daily decisions (4.6 years), 1,689 returns. Price-only leg list of this window (V1/V2/V3 zig-zag phase rule, computed before locking): about 13 bull legs (≥ +50%, including the ×22 leg 2012-10-26→2013-04-09, whose days inside the window count, and the ×10 leg 2013-10-02→2013-12-04) and about 13 bear legs (≤ −30%, including 2013-04, 2013-05→07, 2013-12, three legs in 2014 of −42% to −52%, and 2014-11→2015-01 at −60%) touch the window; exact counts are reported. Phase days = D0+1..D1, clipped to the window.
- Random-timing null: 1,000 seeds (requirement ≥ 200), circular shift k uniform in [30, n−30] of NEW's post-trade exposure series, same costs and funding, no brake (the exposure series already contains the brake's flat spells). Seed s = 20261028 + s.
- INFO window: 2018-03-04 → 2026-09-30 = 3,133 decisions.
- No train/test split is needed inside PRE because nothing is selected or fitted: one rule, two fixed constants stated a priori. The out-of-sample requirement is satisfied by the dataset itself (never used for this rule), not by a split.

## Metrics (all net of costs and funding)
Daily equity at the close, start 10,000. CAGR = (E_end/E_start)^(365/days) − 1. Max DD = min over closes of E/running peak − 1 (never-reset peak starting at 10,000). Calmar = CAGR ÷ |Max DD|. Bull capture = Σ ln(1+r_NEW) ÷ Σ ln(1+r_BH) over bull-phase days. Also reported (not judged): average exposure, number of trades, brake triggers, fraction of days at the 1.5x cap, daily-low max DD, time under water, per-leg capture table, 45 bp stress, NEW_NOBRAKE.

## Pre-registered pass bar (window PRE only, line NEW). All must hold.
- **G1 Fee gate** (RESEARCH_GATE convention): gross CAGR (same engine with costs = 0 and funding = 0) > 0 and net CAGR ≥ 0.5 × gross CAGR (i.e. gross ≥ 2× annual cost+funding drag). If this fails: REJECT, other criteria are not reported as pass/fail.
- **C0 No liquidation**: zero liquidations in PRE.
- **C1 Survive (vs buy-and-hold on drawdown)**: NEW max DD ≥ −30% AND shallower than BH max DD. (V3's −30% line, never-reset peak.) Not informative if BH max DD is shallower than −30% (then C6 = INSUFFICIENT).
- **C2 Bull participation (vs buy-and-hold on return)**: aggregate bull capture ≥ 50%. Reading rule fixed now: if the aggregate is ≥ 50% but fewer than half of the bull legs individually reach ≥ 50% capture, C2 is WARN, not PASS (guards against the ×22/×10 legs carrying the number).
- **C3 Return-or-Calmar vs buy-and-hold** (V1's C3): NEW CAGR ≥ 70% of BH CAGR, OR NEW Calmar > BH Calmar.
- **C4 vs V2 (after fees, same window)**: NEW Calmar > V2b Calmar AND NEW Calmar > V2a Calmar AND NEW CAGR > V2b CAGR AND NEW max DD no worse than V2b's max DD by more than 5 percentage points. (Leverage must add return without taking materially more drawdown than V2's primary line.)
- **C5 Beats random timing, same exposure profile**: the NEW line's Calmar, measured both as the engine value and as the replay of its exposure series (the lower of the two is used), must be above the p95 of the null Calmar distribution = PASS; between p90 and p95 = WARN; below p90 = FAIL. (One pre-registered variant, so p95 and not a corrected percentile; the V1-family multiple-testing caveat is stated in "Honest status" item 5.)
- **C6 Cycle test**: PRE must contain ≥ 1 bull phase and ≥ 1 bear phase by the zig-zag definition (bull leg ≥ +50%, bear leg ≤ −30%), and BH max DD ≤ −30%. If not: INSUFFICIENT.

## Verdict grading
- Overall PASS only if G1, C0..C6 are all PASS. Any FAIL → FAIL. No FAIL but a WARN → "NOT PASS (conditional)" (not promoted). C6 INSUFFICIENT → INSUFFICIENT. G1 FAIL → REJECT.
- **Veto (one-way, information window)**: even if PRE passes, the family is NOT promoted if in the INFO window NEW has any liquidation, or its max DD (never-reset peak, close) is worse than −40%. The veto can only downgrade a PASS; no INFO result can upgrade a FAIL/WARN. Reported verdict in that case: "PASS_PRE_BUT_VETOED (not promoted)".
- Information window numbers are shown regardless, labelled contaminated.
- No parameter, constant, rule, threshold, window or comparator changes after the lock. A different target/lookback/idea is a new family with a new PARAMS.

## What happens next
- FAIL / REJECT / INSUFFICIENT / WARN / VETOED: record in SCOREBOARD, publish the failure page and per-criterion table honestly. Do not retune.
- PASS: only then propose a forward paper-shadow line of this rule (new PARAMS, new ledger, pre-registered like V2/V3, 6/12-month checkpoints). No real money; any small-money step needs the user's explicit approval. A PRE PASS alone is not a track record.

## Honest limits
- 2013–2017 BTC is a different market (thin liquidity, Mt.Gox era, huge daily moves, 56% single-day close move already exists in 2011). 15 bp per side is optimistic for 2013 and is stress-tested at 45 bp (information).
- Daily bars: brake and liquidation are approximated from the daily low and close; intraday order, wicks and ADL are not modelled. Funding is an assumption. Spot prices stand in for perp prices; no perp existed in 2013.
- The −30% line uses a never-reset peak while the brake resets its own peak on re-entry; two consecutive brake exits compound (0.8×0.8 = −36%). This is the V3 design, kept on purpose; it may produce a FAIL on C1. That is a legitimate finding about V3's brake, not a reason to alter it here.
- Zero-volume days (3 in the judged window) are kept.
- The null shifts the exposure series including the brake's flat spells and applies no brake itself; a pure engine-vs-replay difference is reported.

## Selftest and bug policy
- `python3 vt_backtest.py --selftest` uses synthetic random data only (no BTC). It checks that the engine's lines (leverage line with V3's X formula, V2b, BH) equal `regime-bull-v3/paper_track.py::simulate` to relative difference 0.0, that exposure ≤ 1.5×(1+cost), equity > 0, and that null/zig-zag run. Passed before locking.
- Script hash is in SCRIPT.sha256. If the real run crashes or a clear implementation bug is found, the fix must be minimal, logged in BUGLOG.md with the before/after hash and the reason, validated on synthetic data, and the whole run repeated from scratch. A fix may not be motivated by the direction of any result; if in doubt, report the run as invalid rather than patch it to look better.
- Reporting scripts (tables, charts) may be written after the lock; they cannot change any number.

## Run command (tomorrow, 2026-10-28 or later)
```
cd /workspace/anchor-redesign/regime-bull-voltarget && head -1 PARAMS.lock | sha256sum -c && sha256sum -c SCRIPT.sha256 && python3 vt_backtest.py --selftest && python3 vt_backtest.py | tee run.log
```
Outputs: `results.json` (all lines, phase tables, null, criteria, verdict) and `run.log`.

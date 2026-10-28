# REGIME_BULL_SURVIVE_V1 — 预注册参数 / Pre-registered parameters

Written BEFORE any backtest of any variant was run. Only the data-integrity check (row counts, gaps, date range) and the public BTC/ETH
price level (to choose the split and the bull-phase rule) were looked at. No strategy return was computed before this file was locked.

## Why this family exists
Founder intent for Anchor: *in a bear market never get wiped out or forced offline; when a real bull market arrives, genuinely make money.*
Earlier families (carry/basis/direction/multicoin) tried to find an "edge". This one asks a different, simpler question:
can a long-only, 1x, spot-style **regime filter** give most of the bull-market return while cutting the bear-market loss?
Nothing here is new alpha; it is the classic 200-day trend filter family. A FAIL is a fully acceptable outcome.

## Data
- Source: Binance public archive `data.binance.vision`, spot 1d klines, `BTCUSDT` (primary) and `ETHUSDT` (secondary), monthly zips (fetch.sh).
- Range: first available day 2017-08-17 through 2026-09-30 (UTC daily bars). Priced in USDT as proxy for USD.
- Kraken public OHLC only returns ~720 days, so it cannot be used for multi-cycle history.
- Integrity check required before the run: no missing days, no non-positive prices. If violated, report it.
- Execution price model: signal computed on the close of day t-1, executed at the open of day t (24h bars, so close(t-1) ~ open(t)).
  Daily strategy return = weight(t) × (open(t+1)/open(t) − 1); the last day uses its close.

## Hard constraints (all variants)
Long or flat only. No shorts. Weight in [0, 1]. No leverage above 1x. Spot-style, so no liquidation and no funding cost.

## Costs
- 10 bp fee per side + 5 bp slippage per side = 15 bp per unit of turnover (|Δweight|). Main scenario, used for every verdict.
- Stress, informational only: 40 bp fee (Kraken retail spot taker) + 5 bp slippage = 45 bp per side.
- Buy-and-hold is charged the same 15 bp for its one entry at the start of each evaluated window (no exit cost).
- Strategies run continuously across the whole history; windows are slices of the net daily return series, equity rebased to 1.0 at the slice start.

## Variants (exactly 4; no others, no parameter changes after the lock)
Common: SMA values use closes up to and including day t-1 (known at the open of day t). Regime ON = close(t-1) > SMA200(t-1).
- **(a) SMA200**: weight 1 if regime ON, else 0.
- **(b) SMA200_VOLTARGET**: if regime ON, weight = min(1, 0.40 / σ), σ = 60-day stdev of daily log close-to-close returns × √365; else 0.
  Rebalance filter: while in the regime, change the weight only if |target − current| ≥ 0.10; entering from flat sets the weight to target; regime OFF goes to 0 immediately.
- **(c) CROSS_50_200_EXIT20**: Trend state = SMA50 > SMA200. Weight 1 when trend state is true and not stopped out.
  Stop-out: close(t-1) < lowest close of the 20 days before t-1 (days t-21..t-2) → weight 0.
  Re-entry after a stop-out: trend state true AND close(t-1) > highest close of the previous 20 days (t-21..t-2). Flat when the trend state is false.
- **(d) VOLTARGET_DDBRAKE**: variant (b) plus a hard brake on the strategy's own net equity. If equity ≤ −25% from its running peak, weight → 0 (executed next open) and the
  brake is ON. Re-entry only on a NEW regime signal: after the brake triggers, the SMA200 regime must be seen OFF at least once and then turn ON again; only then trade again
  (sizing as in (b)). The equity peak is reset to current equity at re-entry. Before the first trigger the peak runs from the start of the history.

Warm-up: the first tradable day is the first day with 200 closes available (2018-03-05); everything before is excluded from every window, including buy-and-hold.

## Samples
- **In-sample (IS)**: 2018-03-05 → 2022-12-31. Contains the 2018 bear, 2019 range, 2020–21 bull (BTC 4.8k → 67.5k), 2022 bear (−77% peak-to-trough).
- **Out-of-sample (OOS)**: 2023-01-01 → 2026-09-30, evaluated once, only the variant selected on IS.
  Contains the 2023–Oct 2025 bull (BTC trough 15.8k on 2022-11-21 → 124.7k on 2025-10-06) and the Oct 2025 → Jun 2026 bear (BTC → 58.6k), so at least one full bull and one full bear are in OOS.
- The split was chosen by calendar boundary and the known cycle structure, not by looking at any strategy result.

## Bull / bear phase definition (ex-post, used for scoring only, never for trading)
- Turning points from a 20% zig-zag on each asset's own daily close: an up-leg ends at a peak once the close falls ≥20% from that peak; a down-leg ends at a trough once the close rises ≥20% from that trough. Computed once on the full history.
- **Bull phase** = a confirmed up-leg (trough → peak) with trough-to-peak gain ≥ +50%. (Plain 20% legs are mostly noise in crypto, so the scoring bar is raised to +50%; the rule is fixed here.)
  An up-leg still unfinished at the end of data counts only if it is already ≥ +50%.
- **Bear phase** = a confirmed down-leg (peak → trough) with peak-to-trough drop ≥ 30%.
- Phase days: for a leg with turning dates D0→D1, the days D0+1 … D1 inclusive (daily return ≈ close-to-close of that day). Windows are clipped to the sample.
- Bull capture (criterion 2) = Σ daily log net returns of the strategy over all bull-phase days in the sample ÷ same sum for buy-and-hold. Per-leg capture is reported as information.

## Pre-run fee gate (existing RESEARCH_GATE convention, IS, on the selected variant, BTC)
IS annualised gross return ≥ 2 × annualised (fees + slippage). If not met → REJECT, the OOS is not opened.

## Variant selection (IS only, BTC only)
Among variants that pass the fee gate, choose the highest IS Calmar (net CAGR ÷ |max drawdown|, daily-equity drawdown). Ties → fewer trades.
The other three variants' OOS numbers may be printed for information, labelled as not judged, and cannot change the verdict.
ETH uses the same selected variant, unchanged (it is not re-selected).

## Pass bar — all must hold OUT-OF-SAMPLE for the selected variant on BTC (primary)
- **C1 Survive**: OOS max drawdown no worse than −35% AND better (smaller in magnitude) than buy-and-hold's OOS max drawdown.
- **C2 Bull capture**: aggregate bull-phase capture (OOS bull days) ≥ 50%.
- **C3 Return-or-Calmar**: OOS full-window CAGR ≥ 70% of buy-and-hold's OOS CAGR, OR OOS Calmar > buy-and-hold's OOS Calmar. (Full-history numbers shown for information.)
- **C4 Beats random timing**: null = 1000 seeds (≥200 required) of the selected variant's own weight series circularly shifted by a random offset (30 .. N−30 days) within the OOS window.
  That keeps the exposure fraction, the number of trades and the holding-time structure but destroys the timing. Same costs. Metric: OOS Calmar.
  PASS needs the strategy's Calmar above the **discounted p98.75** of the null (p95 corrected for 4 variants: 0.05/4 = 1.25% tail). Between p95 and p98.75 = WARN. Below p95 = FAIL.
- ETH (secondary): the same four tests are reported with the BTC-selected variant. If BTC passes a criterion but ETH fails it, that criterion is marked **WARN**.

## Verdict grading
- Each criterion is PASS / WARN / FAIL as above.
- Overall PASS only if all four are PASS. Any FAIL → FAIL. No FAIL but at least one WARN → "NOT PASS (conditional)", and the family is not promoted.
- Multiple-testing discount: 4 variants (stated; applied in C4 as above and in the wording of the report).
- No re-tuning after seeing results. A different regime idea would be a new family (V2) with new PARAMS.

## Reported but not judged
Time under water, longest drawdown, number of trades, average exposure, bear-phase and bull-phase tables (IS and OOS), 45 bp cost stress, full-history numbers, ETH.

## After
PASS → 90-day paper ledger shadow, then small-money discussion that needs explicit user approval. FAIL → record in SCOREBOARD and cut the family.

# REGIME_BULL_SURVIVE_V1 — REPORT

PARAMS.md sha256: `92e019a0aee0cdd8f71635e469f99b87bcc7178e042ca90bc77cb1b6455f8ef0` (see PARAMS.lock, locked 2026-10-27 10:58:50 Asia/Shanghai before any backtest).
Run: 2026-10-27, `rbs_backtest.py` + `charts_info.py` + `make_report.py`; log in run.log, all numbers in results.json / info_null_all_variants.json.

## 中文摘要（大白话，结论先说）

**结论：不及格（FAIL）。** 按事先锁定的规则，只用样本内（2018-03 到 2022-12）选变体，选出来的是 "50/200 均线交叉 + 20 日低点止损"。它在样本外（2023-01 到 2026-09）的 BTC 表现：年化 8.0%，同期一直拿着不动是 54.0%；最大回撤 -40.7%，拿着不动是 -53.0%；牛市阶段只抓到 29% 的涨幅（要求 ≥50%）。四条及格线里：回撤那条 FAIL、牛市抓取 FAIL、年化/Calmar FAIL、胜过随机择时 FAIL。ETH 也一样不过。

**但有一个重要的发现：**"在熊市活下来"这一半是真的，"在牛市赚到钱"这一半没做到。
- 熊市保护：所有变体的最大回撤都比拿着不动小（样本内 BTC 拿着不动 -77%，趋势过滤版本 -43% 到 -64%；样本外拿着不动 -53%，被选中的 c 版本 -41%，其余三个 -27% 到 -32%），现货 1 倍、没有杠杆，不会被强平。
- 牛市收益：被选中的变体因为反复被假突破洗出去，样本外只剩 8.0% 年化。另外三个变体（只看信息、不作裁决）样本外年化分别是 a 39%、b 和 d 36%，回撤、Calmar 和牛市抓取都看着不错（简单 200 日均线抓取 73%）。可是它们也没有通过"胜过随机择时 p95"这一条（BTC 上分别排在随机分布的第 85/87 百分位），而且事后挑它们是偷看答案，不能算数。
- 一句话：这类"趋势过滤"能明显削掉熊市的亏损，但它的优势没有大到能和"随机择时同样的在场比例"拉开统计差距；而且一旦选错变体，牛市收益会大幅缩水。**不放行实盘，也不进影子期。**如果要继续这个方向，必须作为 V2 重新预注册；没有新的历史可测，只能往前做纸面影子。

## 1. What was tested

- Question: can a long-only, 1x, spot-style regime filter on BTC (primary) and ETH (secondary) keep most of the bull-market return while avoiding most of the bear-market loss?
- Data: Binance public archive, spot 1d klines BTCUSDT and ETHUSDT, 2017-08-17 to 2026-09-30 (3332 daily bars each). Integrity check: BTC {"rows": 3332, "missing_days": 0, "nonpositive": 0, "max_abs_daily_close_move": 0.3950484717412017}; ETH {"rows": 3332, "missing_days": 0, "nonpositive": 0, "max_abs_daily_close_move": 0.44596886079852016}. No gaps or non-positive prices.
- First tradable day 2018-03-05 (200-bar warm-up). IS 2018-03-05..2022-12-31. OOS 2023-01-01..2026-09-30 (one bull 2023→Oct 2025 and one bear Oct 2025→mid-2026 for BTC).
- Costs 15 bp/side (10 fee + 5 slippage); 45 bp/side stress shown for information. Execution: signal on close(t-1), trade at open(t). Weights drift between days and the drift is traded back (turnover is charged on it).
- 4 pre-declared variants; multiple-testing discount: criterion 4 requires the p98.75 of the random-timing null (0.05/4) for a clean PASS.

## 2. Pre-run fee gate and variant selection (IS, BTC)

| Variant | IS gross CAGR | IS annual cost drag | Gross / cost | Gate (≥2×) | IS net Calmar | Entries |
|---|---|---|---|---|---|---|
| a_SMA200 | 18.7% | 0.99% | 18.8× | pass | 0.27 | 16 |
| b_SMA200_VOLTARGET | 21.9% | 0.63% | 35.0× | pass | 0.50 | 16 |
| c_CROSS50_200_EXIT20 | 32.4% | 0.87% | 37.2× | pass | 0.68 | 14 |
| d_VOLTARGET_DDBRAKE | 21.9% | 0.63% | 35.0× | pass | 0.50 | 16 |

All four clear the fee gate easily because these are slow strategies (turnover is tiny compared with the 65 bp wall that killed the basis families). Selection rule (highest IS Calmar among gate-passers): **c_CROSS50_200_EXIT20** (IS Calmar 0.68). ETH uses the same variant unchanged. Note that b and d are identical in IS and on BTC OOS: the 25% equity brake never triggered on BTC.

## 3. Per-variant tables

**BTC in-sample 2018-03-05..2022-12-31** (net of 15 bp/side; buy-and-hold charged one entry)

| Variant | CAGR | Max DD | Calmar | Sharpe | Avg exposure | Entries | Bull capture | CAGR @45bp stress |
|---|---|---|---|---|---|---|---|---|
| Buy & hold | 7.8% | -76.6% | 0.10 | 0.47 | 100% | 1 | 100% | 7.7% |
| a_SMA200 | 17.5% | -64.4% | 0.27 | 0.58 | 42% | 16 | 63% | 15.2% |
| b_SMA200_VOLTARGET | 21.1% | -42.6% | 0.50 | 0.83 | 26% | 16 | 42% | 19.6% |
| c_CROSS50_200_EXIT20 ← selected | 31.2% | -46.1% | 0.68 | 0.91 | 24% | 14 | 51% | 29.0% |
| d_VOLTARGET_DDBRAKE | 21.1% | -42.6% | 0.50 | 0.83 | 26% | 16 | 42% | 20.7% |

**BTC out-of-sample 2023-01-01..2026-09-30 (only the selected variant is judged; the others are information)** (net of 15 bp/side; buy-and-hold charged one entry)

| Variant | CAGR | Max DD | Calmar | Sharpe | Avg exposure | Entries | Bull capture | CAGR @45bp stress |
|---|---|---|---|---|---|---|---|---|
| Buy & hold | 54.0% | -53.0% | 1.02 | 1.16 | 100% | 1 | 100% | 53.9% |
| a_SMA200 | 39.3% | -32.0% | 1.23 | 1.07 | 65% | 17 | 73% | 35.7% |
| b_SMA200_VOLTARGET | 35.5% | -27.2% | 1.31 | 1.08 | 58% | 17 | 66% | 32.2% |
| c_CROSS50_200_EXIT20 ← selected | 8.0% | -40.7% | 0.20 | 0.41 | 33% | 18 | 29% | 5.0% |
| d_VOLTARGET_DDBRAKE | 35.5% | -27.2% | 1.31 | 1.08 | 58% | 17 | 66% | 32.2% |

**BTC full period (information)** (net of 15 bp/side; buy-and-hold charged one entry)

| Variant | CAGR | Max DD | Calmar | Sharpe | Avg exposure | Entries | Bull capture | CAGR @45bp stress |
|---|---|---|---|---|---|---|---|---|
| Buy & hold | 26.0% | -76.6% | 0.34 | 0.69 | 100% | 1 | 100% | 25.9% |
| a_SMA200 | 26.6% | -64.4% | 0.41 | 0.76 | 52% | 33 | 66% | 23.8% |
| b_SMA200_VOLTARGET | 27.2% | -42.6% | 0.64 | 0.95 | 40% | 33 | 50% | 25.0% |
| c_CROSS50_200_EXIT20 ← selected | 20.5% | -48.1% | 0.43 | 0.72 | 28% | 32 | 43% | 17.9% |
| d_VOLTARGET_DDBRAKE | 27.2% | -42.6% | 0.64 | 0.95 | 40% | 33 | 50% | 25.6% |

**ETH in-sample** (net of 15 bp/side; buy-and-hold charged one entry)

| Variant | CAGR | Max DD | Calmar | Sharpe | Avg exposure | Entries | Bull capture | CAGR @45bp stress |
|---|---|---|---|---|---|---|---|---|
| Buy & hold | 6.9% | -90.4% | 0.08 | 0.56 | 100% | 1 | 100% | 6.8% |
| a_SMA200 | 34.8% | -73.9% | 0.47 | 0.79 | 48% | 15 | 61% | 32.3% |
| b_SMA200_VOLTARGET | 32.9% | -36.1% | 0.91 | 1.06 | 22% | 15 | 32% | 31.8% |
| c_CROSS50_200_EXIT20 ← selected | 55.3% | -41.8% | 1.32 | 1.13 | 26% | 14 | 42% | 52.6% |
| d_VOLTARGET_DDBRAKE | 36.6% | -27.7% | 1.32 | 1.21 | 21% | 15 | 30% | 35.5% |

**ETH out-of-sample (information beside the BTC verdict)** (net of 15 bp/side; buy-and-hold charged one entry)

| Variant | CAGR | Max DD | Calmar | Sharpe | Avg exposure | Entries | Bull capture | CAGR @45bp stress |
|---|---|---|---|---|---|---|---|---|
| Buy & hold | 24.0% | -67.6% | 0.36 | 0.65 | 100% | 1 | 100% | 23.9% |
| a_SMA200 | 28.4% | -38.5% | 0.74 | 0.78 | 55% | 13 | 58% | 25.9% |
| b_SMA200_VOLTARGET | 24.8% | -25.0% | 0.99 | 0.86 | 40% | 13 | 44% | 23.0% |
| c_CROSS50_200_EXIT20 ← selected | 7.8% | -47.9% | 0.16 | 0.40 | 29% | 14 | 40% | 5.5% |
| d_VOLTARGET_DDBRAKE | 17.5% | -29.0% | 0.60 | 0.70 | 35% | 12 | 33% | 23.0% |

**ETH full period (information)** (net of 15 bp/side; buy-and-hold charged one entry)

| Variant | CAGR | Max DD | Calmar | Sharpe | Avg exposure | Entries | Bull capture | CAGR @45bp stress |
|---|---|---|---|---|---|---|---|---|
| Buy & hold | 14.1% | -90.4% | 0.16 | 0.58 | 100% | 1 | 100% | 14.0% |
| a_SMA200 | 32.0% | -73.9% | 0.43 | 0.77 | 51% | 28 | 60% | 29.4% |
| b_SMA200_VOLTARGET | 29.3% | -36.1% | 0.81 | 0.97 | 30% | 28 | 36% | 27.9% |
| c_CROSS50_200_EXIT20 ← selected | 32.4% | -47.9% | 0.68 | 0.87 | 27% | 28 | 41% | 29.9% |
| d_VOLTARGET_DDBRAKE | 27.9% | -29.0% | 0.96 | 0.99 | 27% | 27 | 31% | 29.9% |


## 4. Bull-phase and bear-phase breakdowns — selected variant c_CROSS50_200_EXIT20

Phases come from the ex-post 20% zig-zag (bull = leg ≥ +50%, bear = leg ≤ −30%), used for scoring only.

### BTC out-of-sample — bull phases
| Bull leg (asset) | Leg gain | Days | Strategy | Buy&hold | Capture | Strat max DD |
|---|---|---|---|---|---|---|
| 2022-11-21 → 2023-07-13 | 99% | 194 | -4.9% | 89.9% | -6% | -18.3% |
| 2023-09-11 → 2024-03-13 | 190% | 184 | 98.6% | 190.4% | 52% | -11.2% |
| 2024-09-06 → 2025-01-21 | 97% | 137 | 38.1% | 96.7% | 39% | -12.9% |
| 2025-04-08 → 2025-10-06 | 63% | 181 | -11.8% | 63.3% | -19% | -16.0% |

Aggregate bull capture (sum of log returns over 696 bull days): **29%**

### BTC out-of-sample — bear phases

| Bear leg (asset) | Leg drop | Days | Strategy return | Buy&hold return | Strat max DD | B&H max DD |
|---|---|---|---|---|---|---|
| 2025-10-06 → 2026-02-05 | -50% | 122 | -13.3% | -49.5% | -13.3% | -49.5% |

### BTC in-sample — bull phases

| Bull leg (asset) | Leg gain | Days | Strategy | Buy&hold | Capture | Strat max DD |
|---|---|---|---|---|---|---|
| 2018-12-15 → 2019-06-26 | 308% | 193 | 108.5% | 307.8% | 35% | -13.0% |
| 2019-12-17 → 2020-02-14 | 56% | 59 | 0.0% | 56.2% | 0% | 0.0% |
| 2020-03-12 → 2021-01-08 | 745% | 302 | 332.7% | 745.6% | 45% | -10.5% |
| 2021-01-27 → 2021-02-21 | 89% | 25 | 49.5% | 89.1% | 56% | -3.5% |
| 2021-07-20 → 2021-09-06 | 77% | 48 | 0.0% | 76.8% | 0% | 0.0% |
| 2021-09-21 → 2021-11-08 | 66% | 48 | 37.0% | 65.8% | 56% | -11.5% |
| 2022-11-21 → 2023-07-13 | 99% | 40 | 0.0% | 4.8% | 0% | 0.0% |

Aggregate bull capture (sum of log returns over 715 bull days): **51%**

### BTC in-sample — bear phases

| Bear leg (asset) | Leg drop | Days | Strategy return | Buy&hold return | Strat max DD | B&H max DD |
|---|---|---|---|---|---|---|
| 2018-03-04 → 2018-04-06 | -43% | 33 | -19.8% | -42.8% | -19.8% | -42.8% |
| 2018-05-05 → 2018-06-28 | -41% | 54 | 0.0% | -40.7% | 0.0% | -40.7% |
| 2018-07-24 → 2018-12-15 | -62% | 144 | 0.0% | -61.8% | 0.0% | -61.8% |
| 2019-08-08 → 2019-10-24 | -38% | 77 | -19.1% | -38.2% | -19.1% | -38.2% |
| 2019-10-27 → 2019-12-17 | -30% | 51 | 0.0% | -30.5% | 0.0% | -30.5% |
| 2020-02-14 → 2020-03-12 | -54% | 27 | -8.6% | -53.6% | -8.6% | -53.6% |
| 2021-04-13 → 2021-06-08 | -47% | 56 | -30.8% | -47.5% | -30.8% | -47.5% |
| 2021-11-08 → 2022-01-22 | -48% | 75 | -15.9% | -48.1% | -15.9% | -48.1% |
| 2022-03-29 → 2022-06-18 | -60% | 81 | 0.0% | -60.0% | 0.0% | -60.0% |
| 2022-08-13 → 2022-11-21 | -35% | 100 | 0.0% | -35.4% | 0.0% | -35.4% |

### ETH out-of-sample — bull phases

| Bull leg (asset) | Leg gain | Days | Strategy | Buy&hold | Capture | Strat max DD |
|---|---|---|---|---|---|---|
| 2022-11-09 → 2023-04-16 | 92% | 106 | 14.7% | 76.9% | 19% | -10.7% |
| 2023-10-12 → 2024-03-11 | 164% | 151 | 86.8% | 164.0% | 53% | -15.4% |
| 2024-09-06 → 2024-12-08 | 80% | 93 | 5.6% | 79.9% | 7% | -0.1% |
| 2025-04-08 → 2025-06-10 | 91% | 63 | 0.0% | 91.1% | 0% | 0.0% |
| 2025-06-22 → 2025-08-22 | 117% | 61 | 100.6% | 116.9% | 86% | -14.2% |
| 2026-06-25 → 2026-09-21 (unfinished) | 77% | 88 | 12.3% | 77.1% | 16% | -5.1% |

Aggregate bull capture (sum of log returns over 562 bull days): **40%**

### ETH out-of-sample — bear phases

| Bear leg (asset) | Leg drop | Days | Strategy return | Buy&hold return | Strat max DD | B&H max DD |
|---|---|---|---|---|---|---|
| 2024-07-21 → 2024-09-06 | -37% | 47 | -15.6% | -37.1% | -15.6% | -37.1% |
| 2024-12-08 → 2025-04-08 | -63% | 121 | -14.8% | -63.2% | -14.8% | -63.2% |
| 2025-08-22 → 2025-11-21 | -43% | 91 | -29.3% | -42.8% | -29.3% | -42.8% |
| 2026-01-14 → 2026-02-05 | -46% | 22 | 0.0% | -45.5% | 0.0% | -45.5% |
| 2026-04-17 → 2026-06-25 | -35% | 69 | 0.0% | -35.2% | 0.0% | -35.2% |


## 5. Verdict by criterion (OOS, selected variant c_CROSS50_200_EXIT20, BTC primary, ETH secondary)

| # | Criterion | BTC result | ETH result | Verdict |
|---|---|---|---|---|
| C1 | Max DD ≥ −35% AND better than buy-and-hold | strategy -40.7% vs B&H -53.0% → FAIL | -47.9% vs -67.6% → FAIL | **FAIL** |
| C2 | Bull capture ≥ 50% | 29% → FAIL | 40% → FAIL | **FAIL** |
| C3 | OOS CAGR ≥ 70% of B&H, or Calmar > B&H | CAGR 8.0% vs 54.0% (ratio 15%); Calmar 0.20 vs 1.02 → FAIL | CAGR 7.8% vs 24.0% (ratio 33%); Calmar 0.16 vs 0.36 → FAIL | **FAIL** |
| C4 | Calmar above random-timing null (1000 seeds), discounted p98.75 for a PASS, p95 for a WARN | strategy 0.20 sits at the 38th percentile; null p50 0.32, p95 1.77, p98.75 2.73 → FAIL | 0.16 at the 64th pct; null p95 1.08, p98.75 2.71 → FAIL | **FAIL** |

**Overall: FAIL.** (PASS needs all four PASS.) Fee gate: passed (gross ≥ 2× cost, see §2). Number of seeds: 1000 (≥200 required).
Sanity check: the recomputed OOS CAGR from the weight series equals the reported one (7.96% vs 7.96%).

### Not judged, for information only: how the other three variants would have looked OOS (BTC)
These cannot change the verdict. Picking one of them now would be choosing with knowledge of the OOS answer, which is exactly what the pre-registration is meant to prevent.

| Variant | OOS Max DD | OOS Calmar | OOS CAGR | Bull capture | Null percentile (Calmar) | Null p95 | Null p98.75 |
|---|---|---|---|---|---|---|---|
| a_SMA200 | -32.0% | 1.23 | 39.3% | 73% | 85 | 2.27 | 4.06 |
| b_SMA200_VOLTARGET | -27.2% | 1.31 | 35.5% | 66% | 87 | 1.91 | 3.84 |
| c_CROSS50_200_EXIT20 | -40.7% | 0.20 | 8.0% | 29% | 38 | 1.77 | 2.73 |
| d_VOLTARGET_DDBRAKE | -27.2% | 1.31 | 35.5% | 66% | 87 | 1.91 | 3.84 |

Even the three unselected variants would not clear C4 on BTC (best: the 87th percentile). On ETH only the vol-targeted variant reaches 95th percentile, which clears p95 (WARN level) but is far below the discounted p98.75 bar.

## 6. Charts

- `chart_btc_oos_selected.png` — BTC OOS equity (log) and drawdown, selected variant vs buy-and-hold, bull (green) and bear (red) phases shaded.
- `chart_btc_oos_all_variants_info.png` — same, all four variants (information).
- `chart_btc_full_all_variants.png` — BTC 2018-03..2026-09, all variants vs buy-and-hold.
- `chart_eth_oos_selected.png`, `chart_eth_full_all_variants.png` — ETH equivalents.
- `chart_null_calmar.png` — random-timing null distributions with the strategy and p95/p98.75 lines.

## 7. What this can't catch

- **Few independent cycles.** Roughly three bull/bear cycles for two correlated assets. The OOS window holds one big bull and one bear; a pass or fail here is a small sample, not proof.
- **Survivorship and hindsight.** BTC and ETH are the assets that survived and grew. A trend filter looks great on assets that ended up high. The 200-day SMA is a famous rule, so the idea was not found blind.
- **Data is a proxy.** Binance USDT spot, not USD at Kraken. Tether basis, venue-specific outages and Kraken's actual fills are not modelled. Early Binance 2017–18 data is thin.
- **Daily bars only.** Intraday crashes (e.g. wicks through a stop) and gap risk between a signal and the next open are not captured. The max drawdowns are daily close-to-open marks; the real intraday drawdown is worse.
- **"Never forced offline" is only partly tested.** 1x spot cannot be liquidated, but the report cannot catch exchange failure, API/key problems, account freezes, or withdrawal limits. It says nothing about a Kraken evaluation account's own drawdown rules.
- **Costs are flat.** 15 bp/side is assumed on every trade; real slippage in a crash is larger. Stress at 45 bp is shown but not judged. Taxes are not modelled.
- **Selection by IS Calmar can pick a whipsaw-prone variant.** That is what happened with the 50/200 + 20-day-low rule: it did well in the two big IS bulls and was repeatedly stopped out by false breakouts in the OOS choppy bull. That is a real weakness of the pre-registered selection rule, not a bug, and the verdict stands.
- **The random-timing null is generous in a bull market.** Circularly shifted copies of the weights have the same exposure, and in a strongly rising market random exposure earns a lot. Passing it is hard, which is the point: a regime filter is only worth having if it beats luck with the same market exposure.
- Market regimes that have not happened yet (a multi-year sideways market, a slow-bleed bear rather than a crash) are not in the sample, so nothing here says how the filter behaves in them.
- Data ends 2026-09-30 (last complete monthly archive); October 2026 is not included.

## 8. Honest read

The approach delivers half of the founder goal. "Survive bears" works in this data, mostly because a 200-day filter spends roughly 35–75% of the time in cash and 1x spot cannot be liquidated; in the IS the selected family cut BTC's −77% buy-and-hold drawdown to about −46%, and the simpler filters roughly −43% to −64%. "Earn in bulls" did not hold up for the variant the rules picked: it captured only 29% of the OOS bull-phase gains and earned 8.0% a year against 54.0% for buy-and-hold. Under the pre-registered bar the family FAILS, and none of the four variants beats random timing by a clear margin on BTC. The useful lesson is a design one, not a strategy: for Anchor the survival layer (1x, drawdown brake, regime filter as a guardrail) is worth keeping as a risk tool, but this family is not an edge that should be sold or traded with real money as the thing that "makes money in bulls".

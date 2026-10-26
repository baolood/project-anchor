# MULTICOIN_TREND_V1 — Report (2026-10-26, Asia/Shanghai)

**Verdict: FAIL.** Rules locked before any run (PARAMS.md sha256 `4b171ff5…4273`, see PARAMS.lock; `mct_backtest.py`
refuses to run if PARAMS.md changes). Source type: **external** (public time-series-momentum literature, e.g.
Moskowitz–Ooi–Pedersen 2012 and crypto TSMOM follow-ups; reproduced from public description only).

## Where the money was supposed to come from
Slow-moving crypto participants (late retail inflows, underreaction) let big multi-week trends persist; diversification
across 10 coins was meant to cut single-asset noise. Low turnover (weekly, 5% filter).

## Result
- Variants tried: **4** (L ∈ {50,100} × {LONG_FLAT, LONG_SHORT}). IS-selected by net Sharpe: **L50_LONG_FLAT**
  (IS 2020–2023: net ann +33.9%, Sharpe 1.28, maxDD −34%).
- RESEARCH_GATE fee gate (IS, ex-ante): gross 36.8%/yr vs cost 4.4%/yr → **PASS** (8.3×).
- OOS 2024-01 → 2026-09, evaluated once, 143 weeks:

| Criterion | Result | Value |
|---|---|---|
| P1 net ann ≥ 8% | **FAIL** | +4.7% |
| P2 net Sharpe ≥ 0.7 | **FAIL** | 0.31 |
| P3 Sharpe > random-sign p95 (1000 sims) | **FAIL** | 0.31 vs p95 0.86 |
| P4 max DD ≤ 25% | **FAIL** | −25.5% |
| P5 gross/cost ≥ 2× | PASS | 3.6× |
| P6 ≥2 of 2024/2025/2026YTD positive | PASS | +15.5% / −5.0% / +9.2% (simple sums) |
| P7 ex top coin (ETH) still > 0 | PASS | total +19.8% minus ETH +9.2% = +10.6% (simple sums) |

Stress (info only, spot 0.40%+0.05%/side): net ann +2.3%, Sharpe 0.21.

## Interpretation
The 2020–2021 bull run made trend-following look great in-sample; out of sample the edge shrank to ~5%/yr with Sharpe
0.31, which is **indistinguishable from random signs** of the same exposure (p95 0.86). Funding on longs (≈5.7% over OOS)
ate about half of the gross. Cut per playbook — no retuning, no re-run.

## Disclosed implementation choices (PARAMS left these open; fixed before run)
- Inverse-vol weights scaled to 20% target vol with 60-day covariance; then per-coin cap 0.25, gross cap 1.0×.
- Held weights do not drift between weekly rebalances; the 5% filter compares new target vs held weight.
- Weekly return = Monday open → next Monday open (Binance spot 1d archive as price proxy).

## What this test cannot tell
- Binance prices are a proxy; Kraken perps/eval account may differ in listing, funding and fills.
- Whether the Kraken prop eval account even offers these 10 coins was **not** verified.
- 143 OOS weeks is short for a weekly strategy; a true edge of Sharpe ~0.5 could still produce this. But the bar is
  pre-registered and it did not clear it.

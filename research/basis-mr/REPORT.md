# BASIS_MR_V1 — Report (2026-10-23, Asia/Shanghai)

**Verdict: FAIL.** Pre-registered criteria were locked before the run (PARAMS.md sha256 `3a266469…18da`, see PARAMS.lock; the script refuses to run if PARAMS.md changes).
IS-selected variant: **Z2.5_W24_POS** (BTC, Kraken retail). It fails **6 of 7** criteria. Only P4 (no liquidations) passes.
OOS annualized return is **−31.9%**. Costs eat the book: fees+slippage ≈ 67% of starting capital over ~2.8 years, while gross basis capture is ~0.7% and funding net ~0.3%. Edge / costs ≈ **0.015×** (bar was 2×).

This idea is dead under retail fees. Do not iterate into V2 of the same z-score grid — the absolute basis on Binance BTC is only a few basis points, far below round-trip cost.

## Data
- Binance public archive (data.binance.vision), symlinked from funding-carry/data: spot 1h + UM perp 1h klines, BTC and ETH, 2022-01-01 → 2026-10-22. Funding rates included in MTM.
- No re-download. Live CEX APIs remain geo-blocked from the box.
- BTC basis (bp = 0.01%): typically **−5 to +12 bp**. When |z|≥2, mean |basis| is only ~5 bp.
  | Year | mean bp | std | p01 | p99 |
  |---|---|---|---|---|
  | 2022 | −4.3 | 1.9 | −8.4 | +0.5 |
  | 2023 | −2.4 | 4.4 | −6.5 | +9.6 |
  | 2024 | −0.3 | 5.2 | −6.7 | +12.3 |
  | 2025 | −4.3 | 1.2 | −6.6 | −0.3 |
  | 2026 | −4.7 | 1.0 | −7.0 | −1.9 |

## Model
- Signal: rolling z-score of (perp−spot)/spot. Enter at |z|≥Z, exit at |z|≤0.5 or basis crosses 0 or max hold 168h or +30 bp adverse stop.
- Fill: decision at bar-t close → execute at bar-(t+1) close + slippage (no look-ahead on the signal bar).
- Capital: LONG_BASIS at L=2 (~⅔ spot / ⅓ perp margin). SHORT_BASIS (BOTH variants) uses L=2 on both legs + 8% APR spot borrow.
- Fees: KRAKEN_RETAIL spot 0.40% / perp 0.05%; TIER1_CEX spot 0.10% / perp 0.05%. BTC slip 2 bp/leg.
- One position at a time. Liquidation checked on 1h extremes (MM 0.5%).

## Results, BTC (ann. net return on total capital)

| Variant | Fees | IS 2022–23 | OOS 2024–26/10 | OOS max DD | OOS worst month | OOS trades | OOS edge/cost |
|---|---|---|---|---|---|---|---|
| **Z2.5_W24_POS** (selected) | Kraken | −29.2% | **−31.9%** | −66.0% | −6.8% | 334 | 0.015× |
| Z2.5_W72_POS | Kraken | −37.0% | −33.8% | −68.6% | −6.9% | 360 | 0.019× |
| Z2.5_W24_BOTH | Kraken | −57.7% | −54.7% | −89.2% | −12.1% | 568 | 0.010× |
| Z2.5_W72_BOTH | Kraken | −60.7% | −58.5% | −91.5% | −14.7% | 626 | 0.013× |
| Z2.0_W24_POS | Kraken | −70.8% | −72.0% | −97.2% | −14.6% | 1100 | 0.012× |
| Z2.0_W72_POS | Kraken | −70.2% | −71.7% | −97.1% | −14.5% | 1094 | 0.014× |
| Z2.0_W24_BOTH | Kraken | −95.5% | −95.1% | −100% | −29.0% | 2080 | 0.007× |
| Z2.0_W72_BOTH | Kraken | −94.4% | −94.1% | −100% | −30.3% | 1984 | 0.009× |
| Z2.5_W24_POS | Tier-1 | −16.7%* | −13.6% | −33.7% | — | 334 | 0.032× |

\*Tier-1 IS for selected variant approximated from run table; still deeply negative. Every variant loses money in IS and OOS under both fee schedules.

ETH is worse or comparable (higher slip, similar tiny basis) — secondary only; not used for selection.

## Where the money goes (BTC Z2.5_W24_POS, Kraken, OOS 2024-01 → 2026-10)
| Component | % of starting capital |
|---|---|
| Basis P&L (gross convergence) | +0.69% |
| Funding net | +0.32% |
| Fees + slippage | **−67.0%** |
| Borrow | 0% (POS only) |
| **Net (exit-cost adjusted)** | **≈ −57% over 2.81 years (−31.9%/yr)** |

- Time in market ≈ 1.5%. ~167 round trips (334 fills).
- Each Kraken round trip costs ~0.65% of capital; capturing ~5 bp of basis cannot pay for that.
- Even at Tier-1 fees, OOS is still −13.6%/yr — costs fall but the edge stays near zero.
- Liquidations: **zero**. Min margin ratio stayed >35%. Risk of ruin here is fee bleed, not leverage blow-ups.

## 2024–2026 (selected, Kraken)
| Year | Net return |
|---|---|
| 2024 | −32.5% |
| 2025 | −32.8% |
| 2026 YTD (Jan–Oct) | −25.0% |

All three years negative. No regime where this paid.

## Pre-registered criteria (OOS, BTC, Kraken, Z2.5_W24_POS)
| Criterion | Result | Value |
|---|---|---|
| P1 ann ≥ 8% | **FAIL** | −31.9% |
| P2 max DD ≤ 8% | **FAIL** | −66.0% |
| P3 worst month ≥ −3% | **FAIL** | −6.8% |
| P4 no liquidation | PASS | 0 |
| P5 edge ≥ 2× costs | **FAIL** | 0.015× |
| P6 each year > 0 | **FAIL** | all three years negative |
| P7 IS positive | **FAIL** | −29.2% |

**Overall: FAIL.**

## Practical risks / why it fails
1. **Fee vs edge mismatch.** Absolute BTC spot–perp basis extremes are ~5–15 bp. Kraken retail round-trip on the hedged book is ~65 bp of capital. Math does not close.
2. **Z-score is relative, not absolute.** |z|≥2 often means “5 bp vs a 3 bp mean,” not a tradeable dislocation.
3. **Exchange stand-in.** Binance archive prices proxy Kraken. Real Kraken basis could differ, but it would need to be *tens of times* wider to matter under these fees — not observed in prior funding cross-check.
4. **Short-spot borrow** (BOTH variants) only made results worse.
5. Data ends 2026-10-22. Idle cash 0%. Taxes not modelled.

## Recommendation
Log **BASIS_MR_V1 as FAIL** (P1–P3, P5–P7). Do not take this to paper or real money. Do not retune z/window on the same edge — that would be curve-fitting after a locked fail.
A cross-exchange BTC spread (Binance vs Kraken) was considered as alternate primary; with Kraken spot still at 0.40% taker and no free public multi-year Kraken×Binance aligned tape on this box without keys, it faces the same fee wall. Only revisit spread/basis ideas if fees fall below ~0.05–0.10% per side *and* a cleaner absolute-basis or inventory/latency edge is pre-registered as a new V1.

Files:
- PARAMS.md, PARAMS.lock
- basis_backtest.py
- results.json
- data/ → symlink to funding-carry/data

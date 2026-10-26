# FUNDING_CARRY_V1 — Report (2026-10-23, Asia/Shanghai)

**Verdict: FAIL.** The pre-registered criteria were locked before the run (PARAMS.md sha256 `83e50a1b…2148`, see PARAMS.lock; the script refuses to run if PARAMS.md changes).
The IS-selected variant is V0_ALWAYS on BTC with Kraken retail fees. It passes 6 of 7 criteria but fails P1 (return): OOS annualized return is **4.0%**, and the bar was 8%.
It is low risk but low yield. On Kraken retail fees it earns roughly what cash in a money-market fund or T-bills paid in 2024–25, while carrying exchange risk on top.

## Data
- Binance public archive (data.binance.vision): 8h funding, spot 1h and USDT-perp 1h klines, BTC and ETH, from 2022-01-01 to 2026-09-30. Monthly funding files only go up to September 2026.
- Binance, Bybit and OKX live APIs are geo-blocked from the box. The static archive is not.
- Cross-check against Kraken PF_XBTUSD hourly funding (public API, 2025-10-15 → 2026-10-23):
  - Kraken mean funding APR is **3.37%**; Binance over the same window is 3.30%, so the two venues agree.
  - Kraken funding was negative in **31%** of hours. Monthly APR was negative in Feb, Mar and Apr 2026 (−0.8%, −1.0%, −3.4%).

## Model
- Capital split: perp at 2x, so ~2/3 of capital is in spot and ~1/3 is perp margin. All returns are on total capital.
- Fills: at the close of the 1h bar after the decision, plus 2 bp slippage per leg for BTC and 3 bp for ETH.
- Fees:
  - KRAKEN_RETAIL: spot 0.40% taker, perp 0.05%.
  - TIER1_CEX: spot 0.10%, perp 0.05%.
- Rebalance: when perp margin falls outside 30–70% of notional (about a ±20% price move). Both legs pay fees on the rebalanced quantity.
- Liquidation: checked against each 1h high (maintenance margin 0.5%).
- Basis P&L comes straight from the actual spot and perp prices.
- No look-ahead: a funding print at time t can only drive a trade at the close of the next 1h bar.

## Results, BTC (annualized return on total capital, net of everything)
| Variant | Fees | IS 2022–23 | OOS 2024–26/09 | OOS max DD | OOS worst month | OOS trades / rebalances |
|---|---|---|---|---|---|---|
| **V0_ALWAYS** (selected) | Kraken | 3.14% | **4.01%** | −0.46% | −0.13% (2026-04) | 1 / 32 |
| V1 thr 0.005%/8h | Kraken | −12.20% | −1.00% | −7.11% | −1.94% | 45 / 19 |
| V1 thr 0.010%/8h | Kraken | 0.39% | 1.85% | −0.75% | −0.26% | 6 / 10 |
| V1 thr 0.020%/8h | Kraken | 0.32% | 1.77% | −0.75% | −0.26% | 4 / 5 |
| V0_ALWAYS | Tier-1 CEX | 3.74% | 4.51% | −0.35% | −0.13% | 1 / 32 |

ETH, V0_ALWAYS:
- Kraken fees: IS 1.43%, OOS 3.60%.
- Tier-1 fees: OOS 4.40%.
- Worst month: −1.17% (2022-09).

The threshold variants lose because round-trip costs eat the funding. At Kraken's 0.40% spot taker fee, one round trip costs about 0.65% of capital. Being in the market only 15–25% of the time doesn't make that back.

## Where the money comes from (BTC V0, Kraken fees, OOS 2024-01 → 2026-09, % of starting capital)
| Component | % of capital |
|---|---|
| Funding received | +14.69% |
| Funding paid (negative periods) | −1.04% |
| Fees + slippage | −1.92% |
| Basis | −0.31% |
| **Net** | **≈ +11.4% over 2.75 years** |

- Funding is about 7x costs. Costs are not the problem; the problem is that the funding itself is too small.
- Liquidations: zero. The lowest perp margin ratio was 26% of notional OOS and 15.5% IS (2022), against 0.5% maintenance. The rebalance rule kept the short safe.

## 2024–2026 specifically (BTC V0, Kraken fees)
| Year | Net return | Binance BTC mean funding APR | Share of negative funding prints |
|---|---|---|---|
| 2024 | +7.37% | 11.9% | 8% |
| 2025 | +2.90% | 5.1% | 13% |
| 2026 YTD (Jan–Sep) | +1.17% (≈1.6%/yr) | 2.9% | 26% |

Funding has fallen year after year. It paid in 2024, during the ETF and bull-market leverage period. In 2026 it is close to zero.

## What it would make (BTC V0, Kraken fees)
| Capital | At the OOS average (4.0%/yr) | At the 2026 pace (~1.6%/yr) |
|---|---|---|
| $1,000 | ~$40/yr | ~$16/yr |
| $5,000 | ~$200/yr | ~$80/yr |
| $10,000 | ~$400/yr | ~$160/yr |

- Entering and exiting once costs about $65 per $10k on Kraken retail fees.
- There is no capital level where this is clearly worth doing for this user. Even at $10k, the extra over a money-market fund is about $0 to −$250 a year, before counting exchange risk and the time spent.
- Tier-1 fees would add only about 0.5%/yr.

## Pre-registered criteria (OOS, BTC, Kraken fees, V0_ALWAYS)
| Criterion | Result | Value |
|---|---|---|
| P1 ann ≥ 8% | **FAIL** | 4.01% |
| P2 max DD ≤ 5% | PASS | −0.46% |
| P3 worst month ≥ −2% | PASS | −0.13% |
| P4 no liquidation | PASS | 0 |
| P5 funding ≥ 3x costs | PASS | 7.1x |
| P6 each year > 0 | PASS | 2024 +7.4%, 2025 +2.9%, 2026 +1.2% |
| P7 IS positive | PASS | 3.14% |

**Overall: FAIL.**

## Practical risks
1. **Exchange counterparty risk.** Both legs and all the capital sit on one exchange. If the exchange fails, freezes withdrawals or socializes losses, you can lose principal (FTX, 2022). That tail risk is far larger than a 4% yield.
2. **Funding regime change.** Funding follows retail leverage demand. It is already about 3% APR on both Kraken and Binance, and Kraken was negative for three months in 2026. A V0 position pays funding in bear markets.
3. **Can Kraken do both legs?** It needs a normal Kraken Pro account with spot BTC plus Kraken Futures (PF_XBTUSD) permission for the user's jurisdiction and KYC level. This is not verified.
   - The current Kraken prop/eval account is a futures evaluation account. It cannot hold the spot leg, and its rules may not allow a passive hedged position.
   - Kraken Futures does accept BTC as multi-collateral margin per Kraken's docs, which would improve capital efficiency. That is untested here and would be a V2 with new pre-registration.
4. **Operational risks:**
   - Rebalances need monitoring (about 12 a year).
   - Spot↔futures wallet transfers are manual.
   - The model assumes taker fills at the 1h close. Real fills during fast moves would be worse.
5. **Model limits:**
   - Binance prices and funding are a stand-in for Kraken, though the funding cross-check matches.
   - Data ends 2026-09-30.
   - Idle cash earns 0%.
   - Taxes are not modelled.

## Recommendation
Don't pursue funding carry with real money. Log FUNDING_CARRY_V1 as FAIL (P1) in the screener and move to the next idea. A cross-venue basis or spread test would face the same exchange and fee problems, so it is only worth trying if fees are below about 0.1% per side.

Files:
- PARAMS.md, PARAMS.lock (pre-registration)
- carry_backtest.py
- fetch.sh (data download)
- results.json (every run, including monthly and yearly series)
- data/ (raw zips)

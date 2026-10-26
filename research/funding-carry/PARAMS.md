# FUNDING_CARRY_V1 — Pre-registered parameters & pass criteria
Status: LOCKED before any backtest run. SHA-256 of this file is recorded in PARAMS.lock.
Any change after the lock = new version (V2), and V1 results stay as-is.

## Strategy
Delta-neutral cash-and-carry on one venue: long spot + short USDT-margined perpetual, equal coin quantity.
Collect funding when positive; pay it when negative.

## Data (public, no keys)
- Primary: Binance public archive (data.binance.vision): UM perp funding rates (8h), spot 1h klines, UM perp 1h klines.
  BTCUSDT and ETHUSDT, 2022-01-01 → latest available.
- Cross-check: Kraken Futures PF_XBTUSD historical funding (public API, ~last 12 months, hourly).
- (Binance/Bybit live APIs are geo-blocked from the box; the static archive is not.)

## Periods
- In-sample (IS): 2022-01-01 00:00 UTC → 2023-12-31 23:59 UTC
- Out-of-sample (OOS): 2024-01-01 00:00 UTC → end of data
- Variant selection uses IS only. OOS is evaluated once, for the IS-selected variant (all variants reported for transparency).

## No look-ahead
- A funding print at time t is known only at t. Decisions using it execute at the close of the 1h bar starting at t (i.e. t+1h prices).
- Signals use only prints with timestamp <= decision time.
- Fills at 1h bar close of both legs (spot close, perp close) + slippage.

## Capital & margin
- Total capital C = spot notional + perp margin. Perp leverage L = 2 (margin = notional / 2), so ~66.7% spot, ~33.3% perp margin.
- Isolated-style check: perp liquidation if perp margin equity <= maintenance 0.5% of notional, checked against 1h HIGH.
- Rebalance: when perp margin equity / notional falls below 30% or rises above 70% (≈ ±20% price move from last reset),
  re-split equity to target by selling/buying spot and resizing the short; both legs pay fees+slippage on the traded qty.
- Idle cash earns 0% (conservative).

## Costs (two fee scenarios; per side, applied to traded notional)
- KRAKEN_RETAIL (primary, the user's venue): spot taker 0.40%, perp taker 0.05%.
- TIER1_CEX (Binance/OKX/Bybit VIP0 style): spot taker 0.10%, perp taker 0.05%.
- Slippage: BTC 2 bp per leg per trade, ETH 3 bp.
- Basis P&L arises naturally from using actual spot and perp prices at entry/exit/rebalance.

## Variants (fixed grid, no further tuning)
- V0_ALWAYS: enter at start, hold to end (rebalance only).
- V1_T{x}: enter when mean of last 3 funding prints (24h) > x; exit when mean of last 3 prints < 0.
  x ∈ {0.005%, 0.010%, 0.020%} per 8h (≈ 5.5%, 11%, 22% APR).
- Selection rule: highest IS annualized net return on total capital, under KRAKEN_RETAIL fees, BTC.

## Pass criteria (evaluated on OOS, BTC, KRAKEN_RETAIL, IS-selected variant). ALL must pass.
- P1: OOS annualized net return on total capital >= 8.0%.
- P2: OOS max drawdown (mark-to-market, hourly) <= 5.0%.
- P3: OOS worst calendar month >= -2.0%.
- P4: zero liquidations in IS and OOS.
- P5: OOS funding income >= 3x total fees+slippage.
- P6: OOS net return > 0 in each calendar year 2024, 2025, 2026 (YTD).
- P7: the selected variant is also net positive in IS.
Result is reported as PASS / FAIL per criterion. TIER1_CEX and ETH are reported as secondary information only.

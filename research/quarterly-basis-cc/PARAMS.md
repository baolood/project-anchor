# QUARTERLY_BASIS_CC_V1 — Pre-registered parameters & pass criteria
Status: LOCKED before any backtest run. SHA-256 of this file is recorded in PARAMS.lock.
Any change after the lock = new version (V2), and V1 results stay as-is.

## Strategy
Cash-and-carry on BTC quarterly delivery futures vs spot (Binance public archive as price proxy).
Basis b_t = (fut_close_t − spot_close_t) / spot_close_t, in bp = b_t * 10000.
- LONG_BASIS only: long spot + short dated quarterly, equal coin qty.
- Enter only when ex-ante basis_bp >= MIN_BP (fee-gate: MIN_BP >= 130 under KRAKEN_RETAIL ~65bp RT × 2).
- Exit when days_to_expiry <= D_EXIT, or basis_bp <= EXIT_BP, or adverse basis stop STOP_BP from entry, or contract data ends.
- At most one position at a time. No short-basis (no spot borrow).

## Fee gate (ex-ante, locked)
- KRAKEN_RETAIL hedged-book round-trip ≈ 65 bp of capital.
- Hard screen: expected gross capture per RT >= 2× costs ⇒ MIN_BP >= 130 for all variants.
- Variants may only raise MIN_BP above 130, never below.

## Data (public, no keys)
- Binance data.binance.vision: spot BTCUSDT 1h klines; UM dated BTCUSDT_YYMMDD 1h klines for contracts with expiry in 2022-01 → 2026-09.
- Live CEX APIs geo-blocked from the box; static archive is not.
- Venue note: Kraken public instruments include dated FF_XBTUSD_* / FI_XBTUSD_*; this V1 still prices on Binance archive + Kraken fee schedule.

## Periods
- In-sample (IS): 2022-01-01 00:00 UTC → 2023-12-31 23:59 UTC
- Out-of-sample (OOS): 2024-01-01 00:00 UTC → end of available contract data (≤ 2026-09-30 for completed quarters; open contracts marked to last bar without claiming expiry P&L beyond data).
- Variant selection uses IS only. OOS evaluated once for the IS-selected variant (all variants reported).

## No look-ahead
- At bar t close, basis_t uses closes with timestamp <= t.
- Decision at t executes at close of bar t+1 for both legs + slippage.
- Contract list and expiry dates are known from the symbol (YYMMDD); no use of post-expiry prices for that contract.

## Capital & margin
- Total capital C; perp/futures leverage L = 2 (~⅔ spot / ⅓ fut margin).
- Isolated-style liquidation if fut margin equity <= 0.5% of notional on adverse 1h extreme (fut HIGH for short).
- Rebalance when fut margin equity / notional outside 30–70%.
- Idle cash earns 0%.

## Costs
- KRAKEN_RETAIL (primary): spot taker 0.40%, futures taker 0.05%.
- TIER1_CEX (secondary): spot 0.10%, futures 0.05%.
- Slippage: BTC 2 bp per leg per trade.
- Entry, exit, liquidation, rebalance pay fees+slip on traded qty of both legs.

## Fixed knobs (all variants)
- EXIT_BP = 0
- D_EXIT = 2 (days; exit when days_to_expiry <= 2)
- STOP_BP = 80 (exit if basis widens against LONG_BASIS by 80 bp from entry basis)
- ENTRY window: only consider entry when D_EXIT < days_to_expiry <= D_ENTRY_MAX
- One scan per contract life; after exit, no re-entry on the same contract symbol

## Variants (fixed grid; MIN_BP always >= 130)
- M{min}_D{dmax}: MIN_BP ∈ {130, 150, 200}; D_ENTRY_MAX ∈ {90, 60}
→ 6 variants.
- Selection: highest IS annualized net return on total capital under KRAKEN_RETAIL. Ties → lower IS max DD.

## Pass criteria (OOS, BTC, KRAKEN_RETAIL, IS-selected). ALL must pass.
- P1: OOS annualized net return on total capital >= 8.0%.
- P2: OOS max drawdown (hourly MTM) <= 8.0%.
- P3: OOS worst calendar month >= -3.0%.
- P4: zero liquidations in IS and OOS.
- P5: OOS (sum positive gross basis P&L contributions + any funding_net if modeled) / (fees+slippage) >= 2.0. (Delivery futures: funding_net = 0 in this V1.)
- P6: OOS net return > 0 in each calendar year that has >= 1 closed trade; years with zero trades are reported as N/A and do not fail P6.
- P7: selected variant net positive in IS.
- P8 (sample): OOS closed trades >= 3 (sparse-edge guard; FAIL if fewer).
Result PASS/FAIL per criterion. TIER1_CEX secondary only.

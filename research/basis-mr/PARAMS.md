# BASIS_MR_V1 — Pre-registered parameters & pass criteria
Status: LOCKED before any backtest run. SHA-256 of this file is recorded in PARAMS.lock.
Any change after the lock = new version (V2), and V1 results stay as-is.

## Strategy
Spot–perp basis mean-reversion on one venue (Binance public archive as price proxy).
Basis b_t = (perp_close_t − spot_close_t) / spot_close_t.
Signal: rolling z-score of b over window W hours.
- Enter LONG_BASIS (long spot + short perp, equal coin qty) when z_t >= +Z_enter (perp rich).
- Enter SHORT_BASIS (short spot + long perp, equal coin qty) when z_t <= −Z_enter (perp cheap), only for BOTH variants.
- Exit when |z| <= Z_exit, or when basis has crossed 0 toward the entry side (reversion done), or max hold H hours, or stop (basis moves further against entry by STOP_BP from entry basis).
POS_* variants trade LONG_BASIS only (no spot borrow).

## Data (public, no keys)
- Binance public archive (data.binance.vision): spot 1h klines + UM perp 1h klines, BTCUSDT and ETHUSDT, 2022-01-01 → latest available.
- Reuses the same files already under funding-carry/data/ (symlinked). No re-download.
- Funding rates (8h) included in mark-to-market while a position is open (realistic total P&L); the edge under test is basis convergence, so funding is reported separately.
- (Live CEX APIs geo-blocked from the box; static archive is not.)

## Periods
- In-sample (IS): 2022-01-01 00:00 UTC → 2023-12-31 23:59 UTC
- Out-of-sample (OOS): 2024-01-01 00:00 UTC → end of data
- Variant selection uses IS only. OOS is evaluated once, for the IS-selected variant (all variants reported for transparency).

## No look-ahead
- At bar t close, z_t is computed from basis closes with timestamp <= t.
- A decision at t executes at the close of bar t+1 (next hour) for both legs, plus slippage.
- Funding print at time t accrues to a position held through t (same convention as FUNDING_CARRY_V1).

## Capital & margin
- Starting capital C = 1.0 (returns are on total capital).
- LONG_BASIS (cash-and-carry): perp leverage L = 2; qty sized so spot notional + perp margin = deployable equity. Target ~66.7% spot / 33.3% margin.
- SHORT_BASIS (reverse): spot short and perp long both at L = 2 (margin each = notional/2); qty sized to deployable equity. Spot borrow cost = 8% APR charged hourly on short notional (conservative retail borrow proxy).
- Isolated-style liquidation: a leveraged leg is liquidated if its margin equity <= maintenance 0.5% of notional, checked on the adverse 1h extreme (perp HIGH for shorts, perp LOW for longs; spot LOW for long spot, spot HIGH for short spot).
- Idle cash earns 0%.
- One position at a time. Flat between trades. No pyramiding.

## Costs (two fee scenarios; per side, applied to traded notional)
- KRAKEN_RETAIL (primary): spot taker 0.40%, perp taker 0.05%.
- TIER1_CEX (secondary): spot taker 0.10%, perp taker 0.05%.
- Slippage: BTC 2 bp per leg per trade, ETH 3 bp.
- All entries, exits, and liquidations pay fees + slippage on both legs.

## Fixed signal knobs (all variants share these; not tuned)
- Z_exit = 0.5
- Max hold H = 168 hours (7 days)
- Stop: adverse basis move of STOP_BP = 30 bp from entry basis (widening, not convergence)
- Warm-up: need W completed bars before any signal

## Variants (fixed grid, no further tuning)
- Z{z}_W{w}_BOTH: trade both sides; z ∈ {2.0, 2.5}; w ∈ {24, 72}
- Z{z}_W{w}_POS: LONG_BASIS only; z ∈ {2.0, 2.5}; w ∈ {24, 72}
→ 8 variants total.
- Selection rule: highest IS annualized net return on total capital, under KRAKEN_RETAIL fees, BTC. Ties broken by lower IS max DD (more negative is worse).

## Pass criteria (evaluated on OOS, BTC, KRAKEN_RETAIL, IS-selected variant). ALL must pass.
- P1: OOS annualized net return on total capital >= 8.0%.
- P2: OOS max drawdown (mark-to-market, hourly) <= 8.0%.
- P3: OOS worst calendar month >= -3.0%.
- P4: zero liquidations in IS and OOS.
- P5: OOS |gross basis P&L| contribution that is positive, plus net funding, covers fees+slippage+borrow by >= 2.0x
      (i.e. (basis_pnl + funding_net) / costs >= 2.0, with costs = fees+slippage+borrow > 0).
- P6: OOS net return > 0 in each calendar year 2024, 2025, 2026 (YTD).
- P7: the selected variant is also net positive in IS.
Result is reported as PASS / FAIL per criterion. TIER1_CEX and ETH are reported as secondary information only.

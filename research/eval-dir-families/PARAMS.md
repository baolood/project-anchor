# EVAL_DIR_FAMILIES_V1 — three NEW directional families (TSMOM_D_V1, FUNDING_CONTRA_V1, HOUR_SEASON_V1)
Status: LOCKED before any backtest run. SHA-256 recorded in PARAMS.lock. Changes after lock = V2.
Written 2026-10-24 ~12:50 Asia/Shanghai. Research only; public data; no orders/logins/secrets/host changes.
Not in the earlier 9-family screen (MF4 variants, fade, BB/RSI MR, trend pullback, squeeze, Asia range, daily Donchian)
nor reverse/fade-long tests. Multiple-testing note: 3 families × ≤3 variants = ≤9 configs.

## Common
- Instrument: Kraken PF_XBTUSD perp 15m/1h public candles (4h/daily aggregated UTC from 15m, completed bars only).
- Entry next 15m open after the decision; stop-first on 15m; gap fills at worse open; one position at a time.
- Fees 0.04%/side + margin fee 0.033%/day (Kraken Prop). Risk $100/trade, size = 100/(sd + 2×fee×entry). R = net/100.
- IS = 2022-10-03 → 2025-04-01 UTC. OOS = 2025-04-01 → end of data. Variant selection on IS only; OOS run once.

## Families / variants
- **TSMOM_D_V1** (time-series momentum, return sign, time exit): at daily close, if close/close[L days ago] − 1 > 0 → long,
  < 0 → short; hold exactly 7 days (time exit), protective stop 2×ATRd(14); no TP. Variants L ∈ {10, 30, 60}.
- **FUNDING_CONTRA_V1** (crowding fade): signal = mean of last 9 Binance BTCUSDT 8h funding prints (3 days), ranked vs
  previous 540 prints (180 days). Decision at each 8h print (+1 15m bar). Rank ≥ (1−q) → short; ≤ q → long.
  sd = 1.5×ATR4h (≥0.35%), TP 2R, time exit 72h; at most one entry per print. Variants q ∈ {0.10, 0.05}.
  (Binance archive ends 2026-09-30 → OOS ends there.)
- **HOUR_SEASON_V1** (intraday seasonality): on IS only, compute mean 1h log return per UTC hour; choose the contiguous
  4-hour UTC block (wrapping allowed) with the highest mean (long) and the lowest (short). Trade daily at the block start,
  exit at block end; sd = 1×ATR1h×2 (≥0.35%) protective stop. Variants: HS_L (long best block only), HS_LS (both).

## Gate (RESEARCH_GATE adapted to single-leg directional perps)
Hedged-book wall (65 bp) does not apply to a one-leg perp trade; the wall is round-trip commission 8 bp + expected margin
fee (0.033%/day × mean holding days). **Gate: IS-selected variant's IS mean GROSS |captured move| per trade, in the
direction traded (mean signed gross return), ≥ 2 × that wall.** Fail gate → FAIL, no OOS evaluation.

## Selection
Within each family, IS variant with highest IS mean R (net) and ≥ 30 IS trades.

## Pass criteria (OOS, all required; any FAIL → family REJECT)
- P1 OOS mean R (net) > 0.
- P2 OOS trades ≥ 30.
- P3 OOS mean R > 95th percentile of random-direction control (same decision times & exit template, 200 seeds).
- P4 IS mean R > 0 and gate passed.
- P5 MC ultimate P(pass) from 9,954.28 at $100 (EVAL_PASS_PROB_V1 Model A, OOS trades as distribution) ≥ MF4_RECENT + 5 pp.
PASS → next step would be the 90-day ledger sim (NOT run in this V1). No real money.

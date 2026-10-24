# EVAL_PASS_PROB_V1 + EVAL_ACCT_MGMT_V1 — Report (2026-10-24, Asia/Shanghai)

**Verdict: KEEP_R_FIX_100.** The pre-registered rules were locked before any run (PARAMS.md sha256 `d6657988…cf64`,
locked 2026-10-24 12:45:48 +08:00; the scripts refuse to run if PARAMS.md changes). No sizing or account-management rule
raised the no-time-limit pass probability by ≥ 5 pp under both the recent-MF4 distribution (D1) and the zero-edge baseline (D3).
**EVAL_ACCT_MGMT_V1: FAIL** (no variant met the pre-registered test). Multi-instrument (proxy): **FAIL**. It only makes things faster.

## Rules verified (public pages, read 2026-10-24)
- https://support.kraken.com/articles/how-kraken-prop-evaluations-work
- https://support.kraken.com/articles/kraken-prop-faq
- https://www.kraken.com/prop
- Rules for Starter $10k:
  - Target +10%: equity 11,000; positions auto-close when it's touched.
  - Static max drawdown 6%: floor 9,400.
  - Max daily loss 3% of **balance** at 00:30 UTC (08:30 Asia/Shanghai).
  - Unrealized P&L, fees and funding all count in real time.
- **No time limit, no consistency rule, no minimum trading days, no strategy restrictions.**
- Fees are 0.04%/side, plus margin funding of 0.033%/day charged every 4h. Leverage up to 10x.
- Tradable list = "crypto contracts in the market selector". This wasn't re-verified per account and wasn't needed.
- Consequence: **this is a gambler's-ruin problem, not a 60-day race.** Time only matters for patience, for the 10/31
  review, and for the maintenance window. It doesn't affect the rules.

## Inputs
- MF4 trade outcomes (net R per $1 risk, MFE/MAE, duration, gap) at 0.04%/side + 0.033%/day.
- D1 MF4 2024-10→2026-10-23: 137 trades, **−0.071R**, win 20%. Wins average +3.65R, losses −1.03R, worst −1.17R (gap).
- Gross before costs is +0.022R. **Cost drag is ≈ 0.093R per trade**: 0.061R commission + 0.032R funding.
- D2 MF4 2022-10→: 260 trades, +0.214R. This includes the vanished 2022–24 edge, so it's optimistic.
- D3 zero edge: random direction at the same decision bars with the same exits, 20 seeds. 4,874 trades, −0.054R net.
- D4 = D1 at 0.05%/side: −0.085R.

## Model A — Monte Carlo
20,000 paths. Start equity 9,954.28. ~3 years ≈ "no limit". P/F/L = pass / breach / LOCKED. LOCKED = equity too close to
9,400 to open at the rule's minimum risk under the standing "skip if a stop-out would breach" rule (+$30 buffer).

| Rule | 60d pass D1 / D3 | 60d still running D1 | Ultimate pass D1 / D3 | Ultimate breach D1 / D3 | Ultimate LOCKED D1 | Median days to resolve D1 | D2 ultimate pass |
|---|---|---|---|---|---|---|---|
| R_FIX_50 | 0.2 / 0.1 | 92% | 20.0 / 22.0 | 0 / 0 | 78% | 194 | 67.5 |
| **R_FIX_100 (current)** | **9.2 / 8.2** | 46% | **25.6 / 27.2** | 0 / 0 | 74% | 56 | 50.2 |
| R_FIX_150 | 19.2 / 19.9 | 19% | 26.2 / 27.9 | 0 / 0.1 | 74% | 29 | 38.2 |
| R_FIX_200 | 23.6 / 24.6 | 5% | 25.4 / 26.5 | 0 / 0.2 | 75% | 17 | 34.0 |
| R_FIX_250 | 27.8 / 28.9 | 1% | 28.2 / 29.3 | 0.7 / 3.4 | 71% | 15 | 36.4 |
| R_FIX_300 | 0 | 100% | 0 (never trades) | 0 | 0 | – | 0 |
| R_FLOORFRAC | 18.6 / 19.1 | 43% | 24.9 / 26.5 | 1.5 / 2.1 | 74% | 53 | 45.1 |
| R_SNAP (bold) | 28.2 / 28.8 | 4% | 30.2 / 31.4 | **8.9 / 7.6** | 61% | 16 | 39.5 |
| R_DAILYSHRINK150 | 20.7 / 20.7 | 22% | 28.5 / 30.1 | 0 / 0.5 | 72% | 34 | 45.4 |
| R_FREQ2_100 | 15.3 / 13.9 | 27% | 25.5 / 27.2 | 0 / 0 | 75% | 35 | 50.0 |
| R_FREQ2_200 | 25.1 / 26.1 | 1% | 25.4 / 26.4 | 0 / 0.2 | 75% | 11 | 34.1 |

D4 (0.05% fee) is 0.5–2 pp below D1 throughout. Full numbers are in `mc_results.json` and `run_mc.txt`.

## Model B — historical replay (cross-check; heavily overlapping weekly starts ≈ 2–4 independent paths)
| Rule | RECENT 60d pass / LOCKED | RECENT end-of-data pass | FULL 60d pass | FULL end pass |
|---|---|---|---|---|
| R_FIX_100 | 4.6% / 37% | 16.7% (15.7% still running) | 20.3% | 42.5% |
| R_FIX_150 | 19.4% / 54% | 26.9% | 32.5% | 38.2% |
| R_FIX_200 | 29.6% / 66% | 29.6% | 36.3% | 36.3% |
| R_SNAP | 30.6% / 55%, breach 7.4% | 30.6% | 37.3% | 38.2% |
| R_DAILYSHRINK150 | 23.1% / 46% | 30.6% | 37.3% | 45.8% |

Same picture: bigger risk is faster, and the final odds are about the same.

## Pre-registered decision
- The threshold was R_FIX_100 + 5 pp on ultimate pass under BOTH D1 and D3: needed ≥ 30.6% (D1) and ≥ 32.2% (D3).
  - Best D1 was R_SNAP at 30.2%: fails, and it adds a 7–9% real breach.
  - Best D3 was R_SNAP at 31.4%: fails.
  - R_DAILYSHRINK150 adds +2.9 pp on both: below the bar.
- **→ Keep $100.** No rule is recommended on the pre-registered criterion.

## Findings (hard numbers, not tuned)
1. **Without a time limit, sizing barely changes the final odds:** about 25–28% for $100–$250, against a fair, frictionless,
   continuous reference of 554/(554+1,046) = 34.6%. The gap comes from three things:
   - the lock-out buffer: at $100 the effective floor is 9,530, which gives 424/(424+1,046) = 28.8%;
   - cost drag of ≈ 0.093R per trade;
   - the skewed 4R payoff.
2. **Sizing mostly buys speed.**
   - $100 needs a median of ~56 days to resolve, with 46% still undecided at 60 days.
   - $150 needs ~29 days; $200 needs ~17.
   - The earlier "5–10% in 60 days" was a time-boxed number. The no-limit number is ≈ 25%.
3. **The daily line caps risk at ≈ $270.**
   - The 3% line on ~9,950 is ≈ $298 of headroom. With a $30 buffer, $300 can never be opened.
   - A trade held across 08:30 Shanghai gets a fresh line at 0.97 × entry balance. Anything above ~$270 can then breach
     on a normal stop. This is where most R_SNAP / R_FIX_250 breaches come from.
4. **Most non-passing paths end LOCKED, not breached (70–75%).** The account still exists, but it can't take the standard
   trade. Continuing at a tiny risk from there wasn't pre-registered and wasn't modeled. It would add little.
5. **With real edge (D2), small size wins** ($50 → 67.5%). With zero or negative edge, it's a coin flip with a fee meter.
   This is the classic bold-play vs timid-play result, and it's why the sizing choice can't fix a missing edge.
6. **Multi-instrument (R_FREQ2 proxy) changes only speed** (ultimate 25.5% vs 25.6%).
   - The earlier altcoin study (`eval-backtest/long/altcoins/REPORT.md`) also found ETH trades negative in 2022-10→2026.
   - It found BTC/ETH daily correlation of 0.82, and higher fail rates.

## Caveats / overfitting
- The bootstrap is i.i.d. Real regimes cluster: four straight long losses in Sep–Oct 2026. Clustering widens outcomes.
  Historical replay gives a lower RECENT $100 figure, 16.7% (with 15.7% unresolved).
- Assumed: target touch via MFE happens before any stop on the same trade. This applies equally to all rules.
- D1 is only 137 trades, and its mean R has a standard error of ≈ ±0.15R. That's the whole reason D3 is the decisive baseline.
- The modeled lock buffer is $30; the actual guard buffer may differ. Mid-trade reset modeling is approximate.

## Files
`PARAMS.md`, `PARAMS.lock`, `lib.py` (trade extraction + vectorised MC), `gen_trades.py`, `trades.json`, `run_mc.py`,
`mc_results.json`, `run_mc.txt`, `run_replay.py`, `replay_results.json`, `run_replay.txt`.

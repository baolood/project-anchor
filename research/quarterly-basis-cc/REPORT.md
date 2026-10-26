# QUARTERLY_BASIS_CC_V1 — Report (2026-10-23, Asia/Shanghai)

**Verdict: FAIL.** Pre-registered criteria locked before the run (PARAMS.md sha256 `cb2ce951…cdaae`, see PARAMS.lock; script refuses to run if PARAMS.md changes).
IS-selected variant: **M130_D60** (MIN_BP=130, D_ENTRY_MAX=60, BTC, Kraken retail). It fails **P1, P5, P6** (passes P2–P4, P7–P8).
OOS annualized return is **−0.17%** (bar 8%). Realized edge/cost **1.78×** (bar 2×). Year 2024 net **−1.26%**.

This idea clears the **ex-ante fee gate by construction** (enter only if basis ≥ 130 bp ≈ 2×65 bp KRAKEN_RETAIL RT) but **does not clear the return bar**. Do not retune the same MIN_BP / D_ENTRY grid after this locked fail.

## Fee gate (pre-lock probe)
See `/workspace/anchor-redesign/_fee_gate_probe/quarterly_basis_probe.json` and RESEARCH_GATE.md §6.
- Unconditional quarterly carry: median basis often **< 130 bp** → would fail hard screen.
- Conditional entry ≥ 130 bp: **passes** hard screen ex-ante; sparse (D-60 clear-gate historically ~7/19 contracts).

## Data
- Binance public archive: spot BTCUSDT 1h + UM dated `BTCUSDT_YYMMDD` 1h, contracts 2022-03 → 2026-09.
- Kraken public instruments include dated `FF_XBTUSD_*` / `FI_XBTUSD_*` (venue not empty); prices here remain Binance proxy + KRAKEN_RETAIL fees.
- Live CEX APIs geo-blocked; static zip OK.

## Model
- LONG_BASIS only; decision at bar-t close → fill bar-(t+1); no look-ahead.
- Exit: days_to_expiry ≤ 2, or basis ≤ 0, or +80 bp adverse widen stop; no re-entry same symbol.
- L=2, rebalance 30–70%, MM 0.5%; delivery futures funding_net = 0 in V1.

## Results (ann. net on total capital)

| Variant | Fees | IS 2022–23 | OOS 2024–26/09 | OOS max DD | OOS trades | OOS edge/cost |
|---|---|---|---|---|---|---|
| **M130_D60** (selected) | Kraken | **+0.10%** | **−0.17%** | −2.34% | 6 | 1.78× |
| M150_D60 | Kraken | +0.03% | −0.17% | — | 6 | 1.82× |
| M200_D60 | Kraken | +0.00% (0 trades) | +0.49% | — | 3 | 2.85× |
| M130_D90 | Kraken | −0.15% | +1.13% | — | 9 | 2.55× |
| M150_D90 | Kraken | −0.04% | +1.15% | — | 7 | 2.72× |
| M200_D90 | Kraken | −0.28% | +0.95% | — | 5 | 2.70× |

Note: M130_D90 / M150_D90 look better OOS but were **not** eligible for selection (IS not best / IS negative). Pipeline forbids cherry-picking OOS winners.

## OOS trades (selected M130_D60)
| Contract | Entry basis | Exit | Net (approx % capital) | Reason |
|---|---|---|---|---|
| BTCUSDT_240329 | 145 bp | 248 bp | −2.02% | STOP_WIDEN |
| BTCUSDT_240628 | 180 bp | −1 bp | +0.54% | BASIS_FLAT |
| BTCUSDT_240927 | 202 bp | −2 bp | +0.52% | BASIS_FLAT |
| BTCUSDT_241227 | 172 bp | 21 bp | −0.30% | EXPIRY_NEAR |
| BTCUSDT_250328 | 178 bp | 4 bp | +0.44% | BASIS_FLAT |
| BTCUSDT_250926 | 151 bp | 1 bp | +0.36% | BASIS_FLAT |

One widen-stop (−2%) wiped most wins. Gross basis sum ≈ +4.65% of capital vs costs ≈ 2.61% → 1.78× (under 2× bar).

## Pre-registered criteria (OOS, selected, Kraken)
| Criterion | Result | Value |
|---|---|---|
| P1 ann ≥ 8% | **FAIL** | −0.17% |
| P2 max DD ≤ 8% | PASS | −2.34% |
| P3 worst month ≥ −3% | PASS | −1.08% |
| P4 no liquidation | PASS | 0 |
| P5 edge ≥ 2× costs | **FAIL** | 1.78× |
| P6 years with trades > 0 | **FAIL** | 2024 −1.26% |
| P7 IS positive | PASS | +0.10% ann / final>1 |
| P8 OOS trades ≥ 3 | PASS | 6 |

**Overall: FAIL.**

## Recommendation
Log **QUARTERLY_BASIS_CC_V1 as FAIL**. Do not take to paper/real money. Do not retune MIN_BP/D_ENTRY on the same edge.
Even the best OOS grid points (~1.1%/yr) are far below the 8% bar and similar in spirit to FUNDING_CARRY_V1’s thin yield.
Next research must either (a) find an edge with **much larger** ex-ante capture per year at low turnover, or (b) accept that non-directional retail-Kraken carry/basis family is exhausted under current fees until fee tier or instrument set changes — and re-open directional / other families under the same gate + pipeline.

Files: PARAMS.md, PARAMS.lock, quarterly_backtest.py, results.json, data/, run.log

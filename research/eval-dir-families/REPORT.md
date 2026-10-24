# EVAL_DIR_FAMILIES_V1 — Report (2026-10-24, Asia/Shanghai)

**Verdict: all three FAIL.** TSMOM_D_V1 FAIL (P3). FUNDING_CONTRA_V1 FAIL (gate/P4, P3). HOUR_SEASON_V1 FAIL (gate/P4, P1, P3, P5).
PARAMS.md sha256 `4657ac56…7b39`, locked 2026-10-24 12:46:04 +08:00, before any run. The script asserts the hash.
Setup:
- Data: Kraken PF_XBTUSD 15m/1h. Funding signal from Binance BTCUSDT 8h (archive to 2026-09-30).
- Costs: 0.04%/side + 0.033%/day. Risk $100.
- Periods: IS 2022-10-03→2025-04-01; OOS 2025-04-01→2026-10-23.
- Selection was done on IS only.

| ID | IS-selected | IS n / mean R | IS gross bp vs gate (2× wall) | OOS n / mean R | Random p95 (200 seeds) | MC ult pass @ $100 (OOS trades) | Criteria failed | Verdict |
|---|---|---|---|---|---|---|---|---|
| **TSMOM_D_V1** | L30 | 140 / +0.108 | 68.6 vs 58.4 ✓ | 88 / **+0.046** | +0.139 | 45.5% (vs MF4 25.6%) | **P3** | **FAIL** |
| **FUNDING_CONTRA_V1** | q10 (forced pick; both variants negative) | 179 / −0.048 | −11.1 vs 26.6 ✗ | 100 / +0.149 (info only) | +0.166 | 62.7% (info only) | **Gate/P4**, P3 | **FAIL** |
| **HOUR_SEASON_V1** | HS_L (long 21:00–01:00 UTC) | 910 / −0.036 | 6.2 vs 17.0 ✗ | 570 / −0.058 | −0.034 | 3.5% | Gate/P4, P1, P3, P5 | **FAIL** |

Other variants (IS / OOS info only):
- TSMOM L10: +0.041 / +0.011. L60: +0.100 / +0.025.
- FUNDING q05: −0.146 / +0.117.
- HOUR HS_LS: −0.045 / −0.049.

## Notes and skepticism
- **Procedural deviation (disclosed).** PARAMS said "fail gate → no OOS evaluation". The script still computed OOS for the
  two gate-failed families. Those OOS numbers are labelled info-only, and the verdict uses the gate as written.
- **FUNDING_CONTRA_V1 looks good OOS (+0.15R), but it's a sign flip.**
  - IS was negative for both variants (−0.05 / −0.15R).
  - OOS is still below the random-direction p95 (+0.166).
  - Adopting it now would mean choosing on OOS. That's exactly what the pipeline forbids.
  - It can only come back as a new FUNDING_CONTRA_V2, pre-registered, and tested on data after 2026-10-24.
- **TSMOM_D_V1 is positive in both IS and OOS and passes the cost gate.**
  - But OOS +0.046R over 88 trades sits well inside the random range (p95 +0.139).
  - Its 45.5% MC figure comes from the bootstrap: low variance per trade plus a slightly positive sample mean. It isn't
    evidence of edge.
  - A random-direction weekly hold with the same exits would show a similarly high spread.
  - Keep it on a paper watchlist at most.
- **HOUR_SEASON_V1 has a tiny IS hour-of-day drift** (≈ 6 bp per 4h block). That's below the 8 bp commission wall, and it
  vanished OOS (0.8 bp).
- Multiple testing: 7 configs. No family passed, so there's no false-positive risk to manage.
- The **90-day ledger sim and real money are not triggered** (pipeline stops at OOS).

## Files
`PARAMS.md`, `PARAMS.lock`, `fam.py`, `results.json`, `run.txt`.

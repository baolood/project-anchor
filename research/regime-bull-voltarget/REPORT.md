# REGIME_BULL_VOLTARGET_V1 — REPORT

PARAMS.md sha256: `c5870c116583d786f9728fe0ae08c716dadd2c2e449259dafdf5c4bb8c51a9d6` (see PARAMS.lock, locked 2026-10-27 23:46:43 Asia/Shanghai before any backtest of this rule).
Run: 2026-10-28 10:37 Asia/Shanghai, `vt_backtest.py` (sha256 after fix `a05302d9…2712`, see BUGLOG.md); log in run.log, all numbers in results.json. Run once (plus one crashed attempt that produced no output, see §8).

## 中文摘要（大白话，结论先说）

**结论：不及格（FAIL）。** 规则事先锁定：200 日均线之上才持有，仓位 = min(1.5, 0.60/波动率)，沿用 V3 的 20% 回撤刹车。裁决窗口是 Anchor 从没用过的 Bitstamp 2013-01-01 到 2017-08-16。结果：年化 78.7%，同期拿着不动 250.3%；最大回撤 −37.1%（及格线 −30%），拿着不动 −84.9%；牛市只抓到 26.7% 的涨幅（要求 ≥50%）；Calmar 2.12，拿着不动 2.95，V2(b) 3.81，V2(a) 3.62。8 条里 G1、C0、C5、C6 过，C1–C4 不过。Binance 2018–2026 信息窗口（已被看过，只能一票否决）回撤 −55.1%，也会否决。

**最重要的发现：毁掉牛市参与度的是从 V3 继承来的 20% 回撤刹车。** 平均仓位只有 0.17；同样规则去掉刹车（仅供参考）平均仓位 0.68、年化 237%（但回撤 −57.6%）。刹车 5 次触发，每次触发后要等价格先跌破 200 日线再站回去才重新入场，所以 2016–2017 年价格一直在均线上方的几段大牛市全程空仓（这些段抓取率为 0）。这是关于 V3 纸面影子设计的信息，**V3 规则继续锁定，不做任何修改**；也不重调、不重跑本族。

## 1. What was tested

- Question: does volatility-targeted sizing above 1x (constant-risk, max 1.5x) on BTC, inside an SMA200 regime filter and V3's 20% drawdown brake, keep bull-market participation while surviving bears — judged against BTC buy-and-hold on return AND max drawdown?
- Rule (line NEW): regime ON iff close > SMA200; exposure X(t) = min(1.5, 0.60 / σ60(t)), 0.10 rebalance band, 15 bp/side, flat funding 0.03%/day on carried notional, daily-low liquidation check, V3's hard brake at 0.80 × peak (re-entry only after regime OFF then ON).
- Judged window PRE: Bitstamp BTCUSD daily, 2013-01-01 → 2017-08-16, 1,689 decisions; never used by any Anchor strategy test. Integrity: 2,165 rows 2011-09-13..2017-08-16, 0 missing days, 0 non-positive, 0 low>close.
- INFO window (contaminated, veto only): Binance BTCUSDT 2018-03-04 → 2026-09-30, 3,133 decisions. Integrity: 3,332 rows, 0 missing, 0 non-positive, 0 low>close.
- Comparators: BH, V2b (min(1, 0.40/σ), spot), V2a (plain SMA200, spot), NEW_NOBRAKE (information only).

## 2. Variants and multiple testing

- Variants in this family: **1** (one rule, two constants fixed a priori: target 0.60, cap 1.5). Nothing selected, no grid.
- Context: this is the fourth look at the same BTC regime-filter idea — V1 (4 variants, FAIL on Binance 2023–2026 OOS), V2 and V3 (forward paper shadows, running, not judged). The judged window is a different, earlier dataset to limit contamination, but the idea itself is not new; a pass here would only have meant "worth a forward shadow".

## 3. Results, judged window PRE (net of 15 bp/side and funding)

| Line | CAGR | Max DD (close) | Calmar | Avg exposure | Trades | Notes |
|---|---|---|---|---|---|---|
| NEW (judged) | 78.7% | -37.1% | 2.12 | 0.17 | 44 | 5 brake triggers, 0 liquidations, intraday-low DD -48.7%, at 1.5x cap 0.7% of days |
| NEW_NOBRAKE (info) | 237.1% | -57.6% | 4.12 | 0.68 | 125 | not judged |
| V2b | 155.5% | -40.8% | 3.81 | 0.46 | 77 | spot, no funding |
| V2a | 256.3% | -70.9% | 3.62 | 0.72 | 25 | spot, no funding |
| Buy & hold | 250.3% | -84.9% | 2.95 | 1.00 | 1 | |

Stress 45 bp/side (information): NEW CAGR 76.1%, DD -39.7%, Calmar 1.92; V2b 151.6% / -43.2%; V2a 250.6% / -72.2%; BH 250.1% / -84.9%.

Phases (ex-post 20% zig-zag, scoring only): 13 bull legs, 13 bear legs, 853 bull days. Aggregate bull capture **26.7%**; legs with ≥50% capture: **2 of 13** (2013-07→09 59%, 2015-08→11 ~100%). Eight of 13 bull legs had 0% capture, including all five 2016–2017 legs: 2016-01→06 (153 days), 2016-08→2017-01 (155 days), 2017-01→03, 2017-03→06 and 2017-07→08. Bear side: NEW was flat in 12 of 13 bear legs; the one exception (2014-06→10) lost -18.5% vs BH -51.7%.

## 4. Verdict by criterion (PRE, line NEW)

| # | Criterion | Bar | Result | Verdict |
|---|---|---|---|---|
| G1 | Fee gate: net CAGR ≥ 50% of gross | ≥ 0.5 × 84.8% | net 78.7% / gross 84.8% = 0.93 | **PASS** |
| C0 | No liquidation | 0 | 0 | **PASS** |
| C1 | Max DD ≥ −30% AND shallower than BH | ≥ −30%; BH −84.9% | −37.1% (shallower than BH, but beyond −30%) | **FAIL** |
| C2 | Aggregate bull capture ≥ 50% (WARN if most legs < 50%) | ≥ 50% | 26.7% (2/13 legs ≥ 50%) | **FAIL** |
| C3 | CAGR ≥ 70% of BH, OR Calmar > BH | ≥ 175.2%, or Calmar > 2.95 | 78.7% (31% of BH); Calmar 2.12 | **FAIL** |
| C4 | vs V2: Calmar > V2b and > V2a, CAGR > V2b, DD ≤ V2b's + 5 pp | 3.81 / 3.62 / 155.5% / ≥ −45.8% | Calmar 2.12, CAGR 78.7%, DD −37.1% (only the DD part holds) | **FAIL** |
| C5 | Calmar > random-timing p95 (1000 seeds; lower of engine/replay) | > 2.08 (p90 1.61) | engine 2.12 → 95.0th pct; replay 3.24 → 99.1st pct; lower = 2.12 | **PASS** (borderline) |
| C6 | ≥1 bull and ≥1 bear phase; BH DD ≤ −30% | yes | 13 bull / 13 bear; BH −84.9% | **PASS** |

**Overall PRE: FAIL** (C1, C2, C3, C4 fail). No WARN applies.

**INFO window veto (one-way):** NEW max DD −55.1% (limit −40%), 0 liquidations → veto flag raised. It cannot change a FAIL; recorded for completeness. INFO numbers (contaminated, not evidence): NEW CAGR 10.8%, DD −55.1%, Calmar 0.20, avg exposure 0.34, 10 brakes; NEW_NOBRAKE 30.5% / −59.6%; V2b 27.2% / −42.7%; V2a 26.6% / −64.4%; BH 26.0% / −76.6%; bull capture 29.9%; random-timing percentile 77.6 (engine) / 85.1 (replay), p95 0.53.

**Final: FAIL.**

## 5. Comparison to random timing

The null circularly shifts NEW's own post-trade exposure series (same exposure profile, same costs and funding). In PRE, null p50 Calmar 0.26, p90 1.61, p95 2.08, max 4.85. NEW's engine Calmar 2.12 is just over p95 (95.0th percentile); its exposure replay gives 3.24 (99.1st). The gap (replay CAGR 92.1% vs engine 78.7%) is because the replay ignores the brake's gap fills (the selftest prints the same caveat). So the timing of *when* NEW was in the market was better than luck at the margin — but because it was in the market only 17% of the time, the absolute return stayed far below buy-and-hold and both V2 lines. In the INFO window it does not beat random timing (77.6th percentile).

## 6. Fee check

Costs are not the problem: gross CAGR 84.8% vs net 78.7% (cost + funding drag ≈ 6 pp/yr, net/gross 0.93, G1 PASS). At 45 bp/side the result barely moves (76.1%). Turnover is low (44 trades in 4.6 years). The 0.03%/day funding is charged on NEW only (not on V2/BH), which slightly favours the comparators; with average exposure 0.17 the drag is small and does not explain the gap to V2b (155.5%).

## 7. Parameter sensitivity

**Not tested.** One pre-registered variant (target 0.60, cap 1.5, 60-day vol, SMA200, V3 brake). No other target, cap, lookback or brake level was run, and none will be in this family (PARAMS: a different target is a new family). So this report cannot say whether the failure is specific to 0.60/1.5 or general. The NEW_NOBRAKE line is the only "what if" and it is information, not a tested variant.

## 8. Bug log note

The first run (10:37:01) crashed on an off-by-one in a lookback assertion (`i0 >= SMA_WIN` instead of `SMA_WIN − 1`) while setting up the INFO window, before any result was written. One-line fix, hash before `0fb97549…b6ca` (SCRIPT.sha256, read-only and kept; original script kept), after `a05302d9…2712` (SCRIPT.after-fix.sha256). The judged PRE window is not affected by the guard. Whole run repeated once from scratch (10:37:02). Synthetic selftest on the fixed script passed (diff vs V3 engine 0.0). BUGLOG.md was missing when this report was written and was reconstructed from the files; see BUGLOG.md.

## 9. Key lesson — about V3's brake (V3 stays locked)

- The inherited V3 20% drawdown brake is what destroyed bull participation in 2013–2017. With the brake: average exposure 0.17, CAGR 78.7%, bull capture 26.7%. Same rule without the brake (info only): average exposure 0.68, CAGR 237.1% (Calmar 4.12), but DD −57.6% — so the brake also did its job on drawdown.
- Mechanism (from the rules, consistent with the leg table): after a brake exit the line may only re-enter after the regime is seen OFF and then ON again. In a long bull where price stays above SMA200 for months (2016–2017), that never happens, so the line sits flat through the whole leg (0% capture on all five 2016–2017 bull legs). Two consecutive brake exits also compound (0.8 × 0.8 = −36%), which is how a 20% brake still produced −37.1% against the −30% line — PARAMS predicted this possibility.
- This is information about the design of the running V3 paper track (REGIME_BULL_LEV15_V3): in a strong, volatile bull it may spend long stretches flat after a brake. **V3's rules are locked and are NOT changed** because of this; its forward checkpoints (2027-04-27, 2027-10-27) are judged on V3's own pre-registered bar. Any brake redesign would be a new, separately pre-registered family, judged on data it has not seen.

## 10. What this test cannot tell us

- **One rule, one window.** 4.6 years of a very different market (thin Bitstamp liquidity, Mt.Gox era, ×22 and ×10 legs in 2013). Bull capture is dominated by a few huge legs.
- **Not truly blind.** BTC's 2013–2017 history is public and known in outline to the author; the 0.60 target was motivated by Binance-era knowledge. The window is "unseen for this rule", not unknowable.
- **No perp existed in 2013–2017.** Spot prices stand in for perp prices; funding is a flat assumption; 15 bp/side is optimistic for 2013 (45 bp stress shown).
- **Daily bars.** Brake and liquidation fills are approximated from the daily low/close; the intraday-low drawdown (−48.7%) is much worse than the close-based −37.1%.
- **Parameter sensitivity unknown** (§7). Whether a different brake or no brake would pass on unseen data is not answered here — NEW_NOBRAKE's −57.6% DD would fail C1 anyway.
- **Says nothing about the Kraken evaluation account** or its own drawdown rules, and nothing about real fills or exchange risk.
- **3 zero-volume days** in the judged window were kept.

## 11. Conclusion

FAIL. Volatility-targeted sizing up to 1.5x, combined with V3's 20% brake, survived bears on paper (flat in 12 of 13 bear legs, no liquidation, timing at the edge of beating random) but did not participate in bulls: 26.7% bull capture, 78.7% a year against 250% for buy-and-hold and 155% for plain V2(b), and its drawdown still broke the −30% line. The family is cut: no retune, no rerun, no change to PARAMS or locked files. The useful output is the lesson about the V3 brake's re-entry rule, recorded here as information; V3 continues unchanged. No real money, no shadow line for this rule.

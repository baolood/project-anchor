# Anchor 策略记分板（一行一个策略族）

停止线：2027-03-31（约 20 个族）前若无一族通过 90 天影子期 → 报告中建议转向风控工具 + 策略测谎机，由用户决定。
已测族数：10（其中 EVAL_ACCT_MGMT_V1 是账户管理规则，不算交易策略）。通过：0。影子跟踪中：0。

| 日期 | 策略族 | 来源类型 | 变体数 | 手续费门槛 (RESEARCH_GATE) | 样本外结果 | 结论 | 报告 |
|---|---|---|---|---|---|---|---|
| 2026-10-23 | FUNDING_CARRY_V1 | 外部（资金费 carry 公开研究） | 4 | 过（7.1×） | 年化 +4.0% < 8% | FAIL | funding-carry/REPORT.md |
| 2026-10-23 | BASIS_MR_V1 | 自有 | 8 | 不过（0.015×） | 年化 −31.9% | FAIL | basis-mr/REPORT.md |
| 2026-10-23 | QUARTERLY_BASIS_CC_V1 | 外部（期现套利） | 6 | 过（入场即 ≥130bp） | 年化 −0.17% | FAIL | quarterly-basis-cc/REPORT.md |
| 2026-10-24 | TSMOM_D_V1 | 外部（时间序列动量） | 见 PARAMS | 过 | OOS 均值 +0.046R，不胜随机 p95 | FAIL | eval-dir-families/REPORT.md |
| 2026-10-24 | FUNDING_CONTRA_V1 | 自有 | 2 | 不过 | 仅参考 | FAIL | eval-dir-families/REPORT.md |
| 2026-10-24 | HOUR_SEASON_V1 | 外部（日内季节性） | 见 PARAMS | 不过 | OOS −0.058R | FAIL | eval-dir-families/REPORT.md |
| 2026-10-24 | EVAL_ACCT_MGMT_V1（账户管理，非策略） | 自有 | 见 PARAMS | — | 无变体达标 | FAIL（保留固定 $100 风险） | eval-pass-prob/REPORT.md |
| 2026-10-26 | MULTICOIN_TREND_V1 | 外部（多币 TSMOM 文献复现） | 4 | 过（8.3×） | 年化 +4.7%，Sharpe 0.31 < 随机 p95 0.86，回撤 −25.5% | FAIL | multicoin-trend/REPORT.md |
| 2026-10-27 | REGIME_BULL_SURVIVE_V1 | 外部（200 日趋势过滤 / 50-200 交叉，BTC 主、ETH 辅） | 4 | 过（IS 毛收益/成本 ≥18.8×） | 选中 c(50/200+20日低点)：OOS 年化 +8.0% vs 持有 +54.0%，回撤 −40.7% vs −53.0%，牛市抓取 29%，Calmar 0.20 vs 1.02，随机择时第 38 百分位（p95 1.77） | FAIL（C1–C4 全不过；“熊市活下来”部分成立，“牛市赚钱”不成立；非选中变体 a/b 也未过 C4，仅作信息） | regime-bull/REPORT.md |
| 2026-10-27 | REGIME_BULL_SURVIVE_V2（V1 变体 b 前向纸面影子） | 前向影子（BTC 现货，纸面 10,000，无实盘） | 1（+副线 a 不裁决） | 过（沿用 V1） | 运行中，不是结论；检查点 2027-04-27（6 个月）与 2027-10-27（12 个月）；窗口若无完整牛熊则判“证据不足”而非通过 | RUNNING（非结论） | regime-bull-v2/PARAMS.md（sha256 8092f576…051d） |
| 2026-10-27 | REGIME_BULL_LEV15_V3（V2 变体 b ×1.5 杠杆 + 20% 回撤刹车，前向纸面影子） | 前向影子（BTC 永续模拟，纸面 10,000，无实盘） | 1（基准 V2(b) 1x、买入持有，不裁决） | 沿用 V2 | 运行中，不是结论；检查点 2027-04-27 / 2027-10-27；无完整牛熊则“证据不足”；历史回放仅供参考、不算证据 | RUNNING（非结论） | regime-bull-v3/PARAMS.md（sha256 faea68bf…9fcd） |
| 2026-10-28 | REGIME_BULL_VOLTARGET_V1（SMA200 × min(1.5, 0.60/σ) + V3 的 20% 回撤刹车；裁决窗口 Bitstamp 2013-01-01→2017-08-16） | 自有（V1/V2/V3 之后的「波动率调仓」族） | 1 | 过（净/毛 CAGR 0.93） | 年化 +78.7% vs 持有 +250.3%，回撤 −37.1%（线 −30%）vs −84.9%，牛市抓取 26.7%，Calmar 2.12 vs 持有 2.95 / V2b 3.81 / V2a 3.62；随机择时第 95.0 百分位（重放 99.1）；平均仓位 0.17（无刹车 0.68） | FAIL（G1/C0/C5/C6 过，C1–C4 不过；信息窗口 Binance 回撤 −55.1% 也会否决；教训：V3 的 20% 刹车让牛市长期空仓，V3 规则不改） | regime-bull-voltarget/REPORT.md |

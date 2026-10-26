# Anchor 策略记分板（一行一个策略族）

停止线：2027-03-31（约 20 个族）前若无一族通过 90 天影子期 → 报告中建议转向风控工具 + 策略测谎机，由用户决定。
已测族数：8（其中 EVAL_ACCT_MGMT_V1 是账户管理规则，不算交易策略）。通过：0。影子跟踪中：0。

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

# 官方评估合格线 V1.1 签署页

**状态：** 草稿。未冻结。本页不填冻结栏。  
**文档编号：** `ANCHOR_OFFICIAL_PASS_LINE_V1_1_SIGN_OFF`  
**完整条文：** `docs/PROJECT_ANCHOR_OFFICIAL_EVALUATION_PASS_LINE_V1_1_FINAL_DRAFT.md`  
**阈值：** 与 V1 R2 相同，本页不改。  
**实盘：** NO-GO。本页通过也不授权下单。  
**这不是成绩。** 冻结前的账本、2026-10-10 的 808 行复核、合成样本，都只是证据。

A 线是已有的假成交研究基线，看 C1、C2、C3、C4、C5、C8、C9、C10、R0。A 线通过不等于可以用真钱做试点。真钱资格只在 B 线成立，并且 B 线必须连同 C6、C7 一起通过。C6、C7 在 A 线上是「不适用」，既不算失败，也不算通过。

| 编号 | 阈值 | 适用 | 怎么打分 | 数据从哪来 |
|------|------|------|----------|------------|
| C1 | 不少于 90 天 | A 和 B | `(T_score − T0)` 的整天数，不满一天不进位 | 冻结时写下的两个时间，不是账本里的一列 |
| C2 | T0 之后完整平仓不少于 50 笔 | A 和 B | 按文件顺序把开仓和下一次平仓配成一笔；信号、开仓、平仓都在窗口内才计数 | 账本 JSONL |
| C3 | 扣除手续费、资金费、滑点后的净盈亏大于 0 | A 和 B | 平仓净额减去开仓手续费和开仓滑点，再加上资金费。缺一笔资金费就是无法打分，不是 0。账本与外部缓存不一致时不取平均 | 账本；资金费可来自已校验的 `EXTERNAL_PUBLIC_FUNDING_V1` 缓存 |
| C4 | 盈亏比大于 1.10 | A 和 B | 盈利笔毛利合计除以亏损笔毛利绝对值。这不是期望值。与 C3 同一套净额 | 同上 |
| C5 | 最大回撤不超过 8% | A 和 B | 用窗口内净值重算峰谷。不采用账本里存好的回撤列 | 账本 `net_liquidation_equity` |
| C6 | 单笔事前风险不超过 0.5% | 只 B | `risk_amount / equity_at_open`，且必须有事前止损。不用事后盈亏反推 | B 线新行。A 线没有这些字段，状态为不适用 |
| C7 | 单日亏损不超过 2% | 只 B | 上海时区每个交易日的开盘净值到当日最低标记。标记规则是 `MARK_RULE_C7_V1` | B 线权益标记。A 线不适用 |
| C8 | 最大盈利笔不超过正盈利合计的 25% | A 和 B | 与 C3 同一套含资金费净额 | 同上 |
| C9 | 四类治理违规都是 0，且创始人证明盖住整个窗口 | A 和 B | 单独的只追加 JSONL。空文件或缺文件是无法打分，不是 0。窗口内任一违规即失败。通过还要有 `founder_signed` 为布尔 `true` 的覆盖证明 | `docs/PROJECT_ANCHOR_C9_GOVERNANCE_REGISTER_PROCEDURE_V1.md`。从 T0 起写。不写进成交账本 |
| C10 | 每行哈希重算一致，链接不断，编号从 1 连续，没有无法解析的行 | A 和 B | Official V2 配方：除 `row_hash` 外的字段做规范化 JSON，再 SHA-256。第一行 `prev_hash` 为 `GENESIS` | 账本 JSONL。算法在 `eval_scoring/official_v2_row_hash.py` |
| R0 | 官方净盈亏好于随机方向的期望 | A 和 B；A 线硬条件 | 同一组成交。公平硬币的期望毛利是 0，所以期望净额等于负的成本。信号价不是成交价 | 与 C3 相同的官方净额 |

C10 的来源：Mac Official runner 包 `affl-v2-official-auto-ingest-runtime.tgz` 里的 `affl_v2/engine.py`，SHA-256 `299569516edda10e6464246457a5d3e6149ac56900fac04be90fd5fbcef1d1c8`。r2.2 候选 `engine.py` SHA-256 `cd40e5a4186dd3314450388b91a30f06176d97040236a111f5a2093de3506e45`，上述四个函数逐字节相同。创世值来自 `affl_v2/config.py` 第 130 行，是 `GENESIS`。2026-10-22 对一份 2026-10-10 的账本副本做了只读重算：808 行全部对上，链接断裂 0 次。本仓库没有那份副本，这里没有重跑。writer 若改哈希，必须重新核对这份副本再冻结。

表头：打分程序不读权益 CSV。MCP 的 `header_row_mismatches` 是 CSV 列数对不齐，最近一次摘要是 0。JSONL 上最多跳过开头的一行非 JSON 标签（单元格含 `ledger_event_id`、`event_type`、`row_hash`、`prev_hash`、`event_id` 或 `event_hash`）。该行不参与哈希。第一笔事件的 `prev_hash` 仍必须是 `GENESIS`。文件中间的非 JSON 行判 C10 失败。

## English mirror

This page is a draft. Thresholds are unchanged. Freeze fields stay blank. Live trading stays NO-GO. A Line A pass is the research baseline and is not real-money eligibility. Real-money eligibility requires Line B, including C6 and C7, and still does not authorize orders. Pre-T0 rows and the 808-row recompute are evidence, not a grade.

C1: at least 90 days, from the freeze timestamps. C2: at least 50 closed trades fully inside the window, paired in file order. C3: net after fee, funding, and slippage is greater than 0; a missing funding amount stays missing. C4: profit factor greater than 1.10. C5: recomputed max drawdown at most 8%. C6: ex-ante risk at most 0.5%, Line B only. C7: daily loss at most 2%, Line B only. C8: best winner at most 25% of the positive pool. C9: zero governance breaches plus a Founder attestation covering the window; empty or missing register is not scorable. C10: every row hash recomputes, the chain links from `GENESIS`, ids are contiguous from 1, and nothing is unparsed. R0: official net beats the expected random-direction net.

## 冻结清单

填写下表、记下哈希、并另一次提交，才是冻结。本草稿不填。

| 项 | 值 |
|----|----|
| 本签署页 SHA-256 | ____________________ |
| 对应 git commit SHA | ____________________ |
| T0（Asia/Shanghai） | ____________________ |
| T_alloc（若没有新的资金分配规则则留空） | ____________________ |
| 创始人姓名 | ____________________ |
| 签名 | ____________________ |
| R0 随机种子（若启用种子中位数） | ____________________ |
| `T0_FROZEN` | `NO` |

冻结时要做的事：

1. 记录本签署页的 SHA-256，以及包含该记录的 commit SHA。两栏都填上之后再提交一次。
2. 写下 T0 的上海时间。打分从 T0 开始。T0 之前的行保留，不计入成绩。
3. 从 T0 起建立 C9 登记册。删掉模板行。第一行的 `prev_hash` 为 `GOVERNANCE_GENESIS`。此后只追加。
4. 打分时由创始人追加一行 `ATTEST_COVERAGE`：`founder_signed` 为 JSON 布尔 `true`，窗口盖住 `[T0, T_score]`。
5. 若 writer 在冻结前改过哈希，先重新核对 `eval_scoring/official_v2_row_hash.py` 并写下新的 `engine.py` SHA-256。
6. 实盘保持 NO-GO。A 线通过不申请真钱试点。B 线未通过 C6 与 C7 时，不申请真钱试点。

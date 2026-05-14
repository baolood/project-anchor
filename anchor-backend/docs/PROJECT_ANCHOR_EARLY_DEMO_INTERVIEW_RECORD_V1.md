# PROJECT_ANCHOR_EARLY_DEMO_INTERVIEW_RECORD_V1

## 1. 任务结论

本文件用于记录每场 20 分钟 Early Demo 访谈结果。

本轮只定义访谈记录模板，不执行实际访谈，不改代码，不改页面，不改部署。

---

## 2. 访谈记录字段

每场访谈统一记录：

- interview_date
- candidate_id
- channel
- interviewer
- impulse_trade_story
- first_reaction_to_demo
- operation_to_block_first
- willing_to_try (yes/no/maybe)
- willing_to_pay (yes/no/maybe)
- price_range_monthly
- max_concern
- follow_up_action
- signal_level (strong/medium/weak/not_target)

---

## 3. 单场记录模板

```text
[INTERVIEW_ENTRY]
interview_date:
candidate_id:
channel:
interviewer:
impulse_trade_story:
first_reaction_to_demo:
operation_to_block_first:
willing_to_try: yes/no/maybe
willing_to_pay: yes/no/maybe
price_range_monthly:
max_concern:
follow_up_action:
signal_level: strong/medium/weak/not_target
notes:
```

---

## 4. 首轮记录区（初始化）

> 当前未开始实际访谈，以下仅为待填占位。

```text
[INTERVIEW_ENTRY]
interview_date:
candidate_id: C01
channel:
interviewer: baolood
impulse_trade_story:
first_reaction_to_demo:
operation_to_block_first:
willing_to_try: maybe
willing_to_pay: maybe
price_range_monthly:
max_concern:
follow_up_action:
signal_level: weak
notes:
```

```text
[INTERVIEW_ENTRY]
interview_date:
candidate_id: C02
channel:
interviewer: baolood
impulse_trade_story:
first_reaction_to_demo:
operation_to_block_first:
willing_to_try: maybe
willing_to_pay: maybe
price_range_monthly:
max_concern:
follow_up_action:
signal_level: weak
notes:
```

```text
[INTERVIEW_ENTRY]
interview_date:
candidate_id: C03
channel:
interviewer: baolood
impulse_trade_story:
first_reaction_to_demo:
operation_to_block_first:
willing_to_try: maybe
willing_to_pay: maybe
price_range_monthly:
max_concern:
follow_up_action:
signal_level: weak
notes:
```

```text
[INTERVIEW_ENTRY]
interview_date:
candidate_id: C04
channel:
interviewer: baolood
impulse_trade_story:
first_reaction_to_demo:
operation_to_block_first:
willing_to_try: maybe
willing_to_pay: maybe
price_range_monthly:
max_concern:
follow_up_action:
signal_level: weak
notes:
```

```text
[INTERVIEW_ENTRY]
interview_date:
candidate_id: C05
channel:
interviewer: baolood
impulse_trade_story:
first_reaction_to_demo:
operation_to_block_first:
willing_to_try: maybe
willing_to_pay: maybe
price_range_monthly:
max_concern:
follow_up_action:
signal_level: weak
notes:
```

---

## 5. 真实记录（C01 · Early Demo Review 第一轮反馈）

> 仅记录事实摘要，不继续追问。合规：未要账户/API/资金/收益/实盘。

```text
[INTERVIEW_ENTRY]
interview_date: 2026-05-11
candidate_id: C01
channel: whatsapp
interviewer: baolood
impulse_trade_story: (本轮未展开深挖；痛点侧已由反馈侧确认 FOMO / 情绪化 / 风控)
first_reaction_to_demo: 检查清单有价值：能帮助普通交易者放慢速度、减少 FOMO 与情绪化决策
operation_to_block_first: (未单独问「最想拦住的操作」；风险项覆盖已由反馈确认)
willing_to_try: yes
willing_to_pay: unknown
price_range_monthly:
max_concern:
follow_up_action: 整理英文版 Early Demo 页后再请审阅一次；补充方向记为候选 backlog（市场/策略确认、交易后回顾/日志），不承诺完整系统
signal_level: strong
notes: risk_checks_covered: 入场理由、情绪控制、仓位、止损、可接受损失、风险回报。suggested_additions: 市场状况/策略确认检查；交易后回顾/日志。demo_sent=yes；format=英文说明；demo_feedback_collected=PASS
```

### 5.1 真实记录（C01 · Early Demo 英文页第二轮 / 异步截图审阅）

> 非 20 分钟实时访谈；与 §3 模板字段对齐为摘要。不继续追问 C01。不承诺实现完整日志、行情模块、策略系统、连续亏损自动控制或自动交易。

```text
[C01 Early Demo EN Review Round]
C01:
channel: WhatsApp
demo_en_sent: yes
format: screenshots
result: replied
english_page_clear: PASS
checklist_value_confirmed: PASS
risk_checks_coverage_confirmed: PASS
boundaries_clear: PASS
future_ideas_feedback_collected: PASS

positive_feedback:
- layout clean, professional, easy to understand
- focus on discipline rather than prediction is strong
- checklist wording is simple, direct, psychologically effective
- risk checks cover responsible trading fundamentals
- boundaries are clear and increase credibility

suggested_future_improvements: (backlog / future version candidates only)
- strategy confirmation check
- optional market-condition check
- cooldown warning after consecutive losses or trades
- keep interface minimal

no_account_connection_requested: PASS
no_API_key_requested: PASS
no_fund_or_asset_info_requested: PASS
no_profit_promise: PASS
no_real_trading_requested: PASS

closing_line_to_send_once: Thank you, this is very helpful. I’ll keep the first version simple and record strategy confirmation, market-condition check, and cooldown warning as possible future improvements. I won’t add anything complex for now.
```

### 5.2 补充记录（C01 · 真实性 / 优先级简明核对）

> 仍不追问、不收集敏感细节。冷却相关：**仅 backlog 候选**，当前首版不开发冷却功能。

```text
[C01 Authenticity / Priority Check]
picked_one_concrete_option: PASS
validated_priority: cooldown warning
personal_reason_given: PARTIAL/UNKNOWN
AI-assisted_suspected: possible
C01_signal_level_for_this_slice: medium+
C01_line_closed: PASS
no_further_probing: PASS

forbidden_followups_do_not_ask:
- 是否继续测试 / will you keep testing?
- 是否愿意付费 / willingness to pay?
- 用哪个交易所 / which exchange?
- 交易多少次 / how many trades?
- 亏损多少 / how much did you lose?
- 为什么选 cooldown / why did you pick this?
```

---

## 6. 信号判定规则

- `strong`: 明确承认纪律问题 + 愿继续试用或愿讨论付费
- `medium`: 认可方向，有继续意愿，但价值感尚不稳定
- `weak`: 仅泛泛认可或重点转向收益率
- `not_target`: 不具备目标用户特征或明确只求自动赚钱

---

## 7. 使用规则

- 每场访谈结束后 24 小时内补完记录
- `signal_level` 必填，不能留空
- `willing_to_try` 与 `follow_up_action` 必须一致
- 同一候选人多次访谈可新增多条 entry，不覆盖历史

---

## 8. 禁止事项

- 不记录敏感身份与资产信息
- 不记录任何 API key 或交易所凭据
- 不把主观“好感”直接记为 strong，必须有事实支撑
- 不把“无回复”当作访谈完成

---

## 9. 回滚方式

如果未提交：

```bash
cd /Users/baolood/Projects/project-anchor
rm -f anchor-backend/docs/PROJECT_ANCHOR_EARLY_DEMO_INTERVIEW_RECORD_V1.md
git status --short
```

如果已提交：

```bash
cd /Users/baolood/Projects/project-anchor
git revert HEAD
```

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

## 5. 信号判定规则

- `strong`: 明确承认纪律问题 + 愿继续试用或愿讨论付费
- `medium`: 认可方向，有继续意愿，但价值感尚不稳定
- `weak`: 仅泛泛认可或重点转向收益率
- `not_target`: 不具备目标用户特征或明确只求自动赚钱

---

## 6. 使用规则

- 每场访谈结束后 24 小时内补完记录
- `signal_level` 必填，不能留空
- `willing_to_try` 与 `follow_up_action` 必须一致
- 同一候选人多次访谈可新增多条 entry，不覆盖历史

---

## 7. 禁止事项

- 不记录敏感身份与资产信息
- 不记录任何 API key 或交易所凭据
- 不把主观“好感”直接记为 strong，必须有事实支撑
- 不把“无回复”当作访谈完成

---

## 8. 回滚方式

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

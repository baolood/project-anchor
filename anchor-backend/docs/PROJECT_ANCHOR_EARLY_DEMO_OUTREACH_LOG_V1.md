# PROJECT_ANCHOR_EARLY_DEMO_OUTREACH_LOG_V1

## 1. 任务结论

本文件用于记录 Early Demo 第一轮外联执行日志（Outreach Log），确保联系动作可追踪、可复盘、可验收。

本轮只定义日志结构与使用规则，不改代码、不改页面、不改部署配置。

---

## 2. 使用范围

适用文档链路：

- `PROJECT_ANCHOR_EARLY_DEMO_RECRUITING_LIST_V1.md`
- `PROJECT_ANCHOR_EARLY_DEMO_CANDIDATES_V1.md`
- `PROJECT_ANCHOR_EARLY_DEMO_SCRIPT_V1.md`

适用阶段：

- 第一轮 3-5 人 Early Demo 招募与访谈执行

---

## 3. 记录原则

- 每次外联必须有一条记录（无论成功/失败/未读）
- 记录事实，不记录敏感隐私
- 不记录真实 API key、交易所账号、身份证件、资产金额
- 记录结果要可用于 strong / medium / weak / not target 归类
- 所有时间统一使用本地时区（UTC+8）并写明日期

---

## 4. 状态枚举

### 4.1 外联状态（outreach_status）

- `planned`：已列入计划，尚未发送
- `sent`：已发送邀请
- `replied`：已收到回复
- `scheduled`：已约出演示时间
- `completed`：演示已完成
- `declined`：明确拒绝
- `no_response`：超过 72 小时未回复
- `not_target`：筛选后不属于目标用户

### 4.2 信号强度（signal_level）

- `strong`
- `medium`
- `weak`
- `not_target`

---

## 5. 外联日志模板（逐条记录）

每联系 1 位候选人，追加一段：

```text
[OUTREACH_ENTRY]
date:
candidate_id:
priority: P0/P1/P2
channel: private_chat / telegram_group / discord / x_dm / linkedin
script_version: private_v1 / x_v1 / linkedin_v1
outreach_status:
response_summary:
screening_q1_crypto_traded_6m: yes/no/unknown
screening_q2_discipline_issue: yes/no/unknown
screening_q3_rule_check_helpful: helpful/annoying/unknown
demo_scheduled_at:
demo_completed_at:
signal_level: strong/medium/weak/not_target
next_action:
owner:
notes:
```

---

## 6. 执行日志（第一轮）

> 说明：以下为初始空日志。执行外联后在本节持续追加，不覆盖历史。

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C01
priority: P0
channel: private_chat
script_version: private_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: send private_v1 on 2026-05-10
owner: baolood
notes:
```

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C02
priority: P0
channel: private_chat
script_version: private_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: send private_v1 on 2026-05-10
owner: baolood
notes:
```

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C03
priority: P0
channel: private_chat
script_version: private_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: send private_v1 on 2026-05-11
owner: baolood
notes:
```

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C04
priority: P0
channel: private_chat
script_version: private_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: send private_v1 on 2026-05-11
owner: baolood
notes:
```

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C05
priority: P1
channel: telegram_group
script_version: private_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: send private_v1 on 2026-05-12
owner: baolood
notes:
```

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C06
priority: P1
channel: discord
script_version: private_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: send private_v1 on 2026-05-12
owner: baolood
notes:
```

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C07
priority: P1
channel: x_dm
script_version: x_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: post x_v1 and DM on 2026-05-13
owner: baolood
notes:
```

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C08
priority: P1
channel: x_dm
script_version: x_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: post x_v1 and DM on 2026-05-13
owner: baolood
notes:
```

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C09
priority: P2
channel: linkedin
script_version: linkedin_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: send linkedin_v1 on 2026-05-14 (if needed)
owner: baolood
notes:
```

```text
[OUTREACH_ENTRY]
date: 2026-05-09
candidate_id: C10
priority: P2
channel: private_chat
script_version: private_v1
outreach_status: planned
response_summary:
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at:
demo_completed_at:
signal_level: not_target
next_action: send private_v1 on 2026-05-14 (if needed)
owner: baolood
notes:
```

---

## 7. 每日汇总模板（执行日结束后）

```text
[DAILY_OUTREACH_SUMMARY]
date:
sent_count:
replied_count:
scheduled_count:
completed_count:
declined_count:
no_response_count:
strong_count:
medium_count:
weak_count:
not_target_count:
top_risks:
next_day_plan:
```

---

## 8. 质量门槛

外联日志质量通过条件：

- 所有已发送候选人都有对应 OUTREACH_ENTRY
- 状态变化有时间与 next_action
- 筛选三问至少填到 `unknown/yes/no` 级别，不留空结构
- 信号分级明确（strong/medium/weak/not_target）
- 无敏感隐私字段

---

## 9. 禁止事项

- 不在日志中记录真实身份信息
- 不记录交易账户凭据
- 不记录 API key / 钱包私钥 / 助记词
- 不把“未回复”误记成“拒绝”
- 不跳过筛选问题直接判 strong

---

## 10. 回滚方式

如果未提交：

```bash
cd /Users/baolood/Projects/project-anchor
rm -f anchor-backend/docs/PROJECT_ANCHOR_EARLY_DEMO_OUTREACH_LOG_V1.md
git status --short
```

如果已提交：

```bash
cd /Users/baolood/Projects/project-anchor
git revert HEAD
```

# PROJECT_ANCHOR_EARLY_DEMO_OUTREACH_LOG_V1

## 1. 任务结论

本文件用于记录 Early Demo 第一轮外联执行日志（Outreach Log），确保联系动作可追踪、可复盘、可验收。

本轮定义日志结构、**虚构示例表格 + 空表**与使用规则；**示例非真实外联**。不改代码、不改页面、不改部署配置。

## 相关检查入口

- 负责人每日检查顺序与异常上报口径，以 **`LEAD_DAILY_CHECK_GUIDE_V1.md`** 与 **`/lead-check`** 为准（二者在 **`anchor-console`** 仓库；本文件在 **`anchor-backend/docs`**，分仓勿写相对路径硬链）。
- 本文仅记录 Early Demo 外联执行，**不替代**系统运行态判断。
- 若外联过程中发现系统异常，仍按 **`/ops` → `/commands` → `/commands/[id]`** 顺序记录与上报。

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

### 5.1 文本块（逐条追加）

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

### 5.2 表格速记 · 示例（已填，虚构）

> 仅为格式示意，非真实外联事实。

| candidate_id | channel | script_version | date | outreach_status | response_summary |
|--------------|---------|----------------|------|-----------------|------------------|
| C01 | private_chat | private_v1 | 2026-05-10 | sent | 已发私聊话术，待回复 |
| C02 | private_chat | private_v1 | 2026-05-10 | replied | 对方确认收到，询问演示形式 |

### 5.3 表格速记 · 空表（真实数据）

| candidate_id | channel | script_version | date | outreach_status | response_summary |
|--------------|---------|----------------|------|-----------------|------------------|
| C01 | whatsapp | private_v1 | 2026-05-11 | completed | R1+R2 PASS；+ 2026-05-14 优先级/真实性简明核对（cooldown backlog 优先）；见 §6 C01 第二、三、四条 OUTREACH_ENTRY |
| | | | | | |

---

## 6. 执行日志（第一轮）

> 说明：以下为初始空日志。执行外联后在本节持续追加，不覆盖历史。

```text
[OUTREACH_ENTRY]
date: 2026-05-11
candidate_id: C01
priority: P0
channel: whatsapp
script_version: private_v1
outreach_status: scheduled
response_summary: pain_confirmed PASS; tool_value_confirmed PASS; demo_review_interest PASS; first contact round PASS
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at: TBD
demo_completed_at:
signal_level: strong
next_action: send simple demo page when ready; no further chat push per playbooks
owner: baolood
notes: no API key; no fund/asset ask; no profit promise
```

```text
[OUTREACH_ENTRY]
date: 2026-05-11
candidate_id: C01
priority: P0
channel: whatsapp
script_version: private_v1
outreach_status: completed
response_summary: Early Demo R1 feedback PASS. checklist_value: helps slow down, reduce FOMO/emotional entry. risk_checks: entry reason, emotion, size, stop, max loss, risk-reward. suggested_additions: market/strategy confirmation; post-trade review/journal (candidate backlog only, no product commitment).
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at: TBD
demo_completed_at: 2026-05-11
signal_level: strong
next_action: prepare_english_copy_early_demo_page_for_second_review; no further probing per playbook
owner: baolood
notes: demo_sent yes; format English explanation; no account/API/fund/profit/real-trading ask; PASS
```

```text
[OUTREACH_ENTRY]
date: 2026-05-11
candidate_id: C01
priority: P0
channel: whatsapp
script_version: private_v1
outreach_status: completed
response_summary: Early Demo EN R2 PASS (strong). english_page_clear PASS; checklist_value_confirmed PASS; risk_checks_coverage_confirmed PASS; boundaries_clear PASS; future_ideas_feedback_collected PASS. Positive: layout clean/professional; discipline-over-prediction framing; simple checklist wording; risk fundamentals; boundaries build trust. Future ideas (backlog only): strategy confirmation check; optional market-condition check; cooldown after consecutive losses/trades; keep UI minimal. demo_en_sent yes; format screenshots; replied yes.
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at: TBD
demo_completed_at: 2026-05-11
signal_level: strong
next_action: stop_c01_line_no_further_probing; send_one_line_closing_thank_you_only; no_immediate_feature_build_from_suggestions
owner: baolood
notes: no account connection requested PASS; no API key PASS; no fund/asset info PASS; no profit promise PASS; no real trading requested PASS. Suggested closing line to candidate (English, one message): "Thank you, this is very helpful. I’ll keep the first version simple and record strategy confirmation, market-condition check, and cooldown warning as possible future improvements. I won’t add anything complex for now."
```

```text
[OUTREACH_ENTRY]
date: 2026-05-14
candidate_id: C01
priority: P0
channel: whatsapp
script_version: private_v1
outreach_status: completed
response_summary: Authenticity/priority micro-check. picked_one_concrete_option PASS; validated_priority: cooldown warning (after losses or too many trades); personal_reason_given PARTIAL/UNKNOWN; AI-assisted suspected still possible; aggregate C01 signal for this slice medium+ (not absolute strong validation—sparse personal detail). cooldown_warning = backlog candidate only; no v1 implementation.
screening_q1_crypto_traded_6m: unknown
screening_q2_discipline_issue: unknown
screening_q3_rule_check_helpful: unknown
demo_scheduled_at: TBD
demo_completed_at:
signal_level: medium
next_action: send_one_line_closing_thank_you_only_then_stop; no follow-up questions (no why pick / loss amount / trade count / exchange / willingness to pay)
owner: baolood
notes: C01 line closed PASS; no further probing PASS. Do not build cooldown feature now.
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

# PROJECT_ANCHOR_EARLY_DEMO_CONTACT_LOG_V1

## 1. 任务结论

本文件用于记录 Early Demo 第一轮候选人的联系状态。

本轮定义联系记录模板、**虚构示例行 + 空表**与初始全量表；**示例非真实外联**。不执行实际联系动作，不改代码，不改页面，不改部署。

## 相关检查入口

- 负责人每日检查顺序与异常上报口径，以 **`LEAD_DAILY_CHECK_GUIDE_V1.md`** 与 **`/lead-check`** 为准（二者在 **`anchor-console`** 仓库；本文件在 **`anchor-backend/docs`**，分仓勿写相对路径硬链）。
- 本文仅记录 Early Demo 联系状态，**不替代**系统运行态判断。
- 若外联过程中发现系统异常，仍按 **`/ops` → `/commands` → `/commands/[id]`** 顺序记录与上报。

---

## 2. 联系日志字段说明

每条记录至少包含以下字段：

- candidate_id
- priority (P0/P1/P2)
- channel
- planned_contact_date
- message_sent (yes/no)
- replied (yes/no)
- target_fit (yes/no/unknown)
- demo_agreed (yes/no/pending)
- demo_schedule_at
- status
- owner
- notes

---

## 3. 双轨表：示例（已填，虚构）+ 空表（真实数据）

> 下列 **示例行仅为格式示意**，不表示已发生真实外联。真实数据只填入 §3.2 空表或 §4 全量表。

### 3.1 示例记录（已填）

| candidate_id | channel | message_sent | result（status 简写） | notes |
|--------------|---------|--------------|------------------------|-------|
| C01 | private_chat | yes | pending | 已发 Recruiting List 私聊话术，等待回复 |
| C02 | private_chat | yes | replied | 对方表示有兴趣，尚未约演示时间 |

`result` 列可与 §5 状态枚举对应：`pending` / `sent` / `replied` / `scheduled` 等。

### 3.2 空表（可填真实数据）

| candidate_id | channel | message_sent | result | notes |
|--------------|---------|--------------|--------|-------|
| C01 | whatsapp | yes | completed | Early Demo R1：清单/风险/建议已记录；合规 PASS |
| | | | | |

---

## 4. 第一轮联系日志（初始化 · 全量字段）

| candidate_id | priority | channel | planned_contact_date | message_sent | replied | target_fit | demo_agreed | demo_schedule_at | status | owner | notes |
|--------------|----------|---------|----------------------|--------------|---------|------------|-------------|------------------|--------|-------|-------|
| C01 | P0 | whatsapp | 2026-05-11 | yes | yes | yes | yes | TBD | completed | baolood | 首轮外联 PASS；Early Demo R1 反馈 PASS：清单价值、风险覆盖、补充建议已记录（见 INTERVIEW_RECORD / OUTREACH）。未要 API key / 资金 / 实盘。下一动作：仅英文版 Early Demo 页二次审阅，不承诺完整交易日志系统。 |
| C02 | P0 | private_chat | 2026-05-10 | no | no | unknown | pending |  | planned | baolood |  |
| C03 | P0 | private_chat | 2026-05-11 | no | no | unknown | pending |  | planned | baolood |  |
| C04 | P0 | private_chat | 2026-05-11 | no | no | unknown | pending |  | planned | baolood |  |
| C05 | P1 | telegram_group | 2026-05-12 | no | no | unknown | pending |  | planned | baolood |  |
| C06 | P1 | discord | 2026-05-12 | no | no | unknown | pending |  | planned | baolood |  |
| C07 | P1 | x_dm | 2026-05-13 | no | no | unknown | pending |  | planned | baolood |  |
| C08 | P1 | x_dm | 2026-05-13 | no | no | unknown | pending |  | planned | baolood |  |
| C09 | P2 | linkedin | 2026-05-14 | no | no | unknown | pending |  | backup | baolood | only if needed |
| C10 | P2 | private_chat | 2026-05-14 | no | no | unknown | pending |  | backup | baolood | only if needed |

---

## 5. 状态枚举

- `planned`: 已进入联系计划，未发送
- `sent`: 已发送邀请
- `replied`: 对方已回复
- `scheduled`: 已约出演示
- `completed`: 演示已完成
- `declined`: 明确拒绝
- `no_response`: 超过 72 小时未回复
- `not_target`: 筛选后不属于目标用户
- `backup`: 备用候选人，前置候选不足时再联系

---

## 6. 使用规则

- 每次状态变化必须更新 `status` 与 `notes`
- 未发送不可标记为 `replied/scheduled/completed`
- `demo_agreed=yes` 时必须填写 `demo_schedule_at`
- 明确不符合目标用户时，标记 `target_fit=no` 且 `status=not_target`
- 每日结束更新一次当日变更

---

## 7. 禁止事项

- 不记录真实姓名、交易所账号、API key、资产信息
- 不记录身份证件、银行卡、钱包私钥/助记词
- 不把“未回复”记成“拒绝”
- 不跳过筛选问题直接标记 strong

---

## 8. 回滚方式

如果未提交：

```bash
cd /Users/baolood/Projects/project-anchor
rm -f anchor-backend/docs/PROJECT_ANCHOR_EARLY_DEMO_CONTACT_LOG_V1.md
git status --short
```

如果已提交：

```bash
cd /Users/baolood/Projects/project-anchor
git revert HEAD
```

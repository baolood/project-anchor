# PROJECT_ANCHOR_EARLY_DEMO_CONTACT_LOG_V1

## 1. 任务结论

本文件用于记录 Early Demo 第一轮候选人的联系状态。

本轮仅定义联系记录模板与初始表格，不执行实际联系动作，不改代码，不改页面，不改部署。

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

## 3. 第一轮联系日志（初始化）

| candidate_id | priority | channel | planned_contact_date | message_sent | replied | target_fit | demo_agreed | demo_schedule_at | status | owner | notes |
|--------------|----------|---------|----------------------|--------------|---------|------------|-------------|------------------|--------|-------|-------|
| C01 | P0 | private_chat | 2026-05-10 | no | no | unknown | pending |  | planned | baolood |  |
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

## 4. 状态枚举

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

## 5. 使用规则

- 每次状态变化必须更新 `status` 与 `notes`
- 未发送不可标记为 `replied/scheduled/completed`
- `demo_agreed=yes` 时必须填写 `demo_schedule_at`
- 明确不符合目标用户时，标记 `target_fit=no` 且 `status=not_target`
- 每日结束更新一次当日变更

---

## 6. 禁止事项

- 不记录真实姓名、交易所账号、API key、资产信息
- 不记录身份证件、银行卡、钱包私钥/助记词
- 不把“未回复”记成“拒绝”
- 不跳过筛选问题直接标记 strong

---

## 7. 回滚方式

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

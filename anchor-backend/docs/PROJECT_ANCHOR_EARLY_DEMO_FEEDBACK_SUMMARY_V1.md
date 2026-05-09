# PROJECT_ANCHOR_EARLY_DEMO_FEEDBACK_SUMMARY_V1

## 1. 任务结论

本文件用于汇总 3-5 位 Early Demo 访谈后的验证结论，形成下一步唯一动作决策。

本轮仅提供汇总结构与判定规则，不填真实访谈结果，不改代码，不改页面，不改部署。

---

## 2. 汇总指标

每次阶段汇总至少包含：

- interview_count
- strong_count
- medium_count
- weak_count
- not_target_count
- continue_decision (yes/no/hold)
- next_single_product_action

---

## 3. 汇总模板（执行后填写）

```text
[FEEDBACK_SUMMARY]
period:
interview_count:
strong_count:
medium_count:
weak_count:
not_target_count:
top_confirmed_pains:
top_objections:
continue_decision: yes/no/hold
next_single_product_action:
owner:
date:
```

---

## 4. 首轮占位（未开始访谈）

```text
[FEEDBACK_SUMMARY]
period: early_demo_round_1
interview_count: 0
strong_count: 0
medium_count: 0
weak_count: 0
not_target_count: 0
top_confirmed_pains:
top_objections:
continue_decision: hold
next_single_product_action: wait_for_first_3_to_5_interviews
owner: baolood
date: 2026-05-09
```

---

## 5. 继续推进判定规则

可继续推进（`continue_decision=yes`）的最低条件：

- interview_count >= 3
- strong_count >= 1
- (strong_count + medium_count) >= 2
- 至少 1 人愿意继续试用
- 至少 1 人愿意讨论付费或价格

暂缓（`hold`）条件：

- interview_count < 3
- 或 strong_count = 0 且 medium_count <= 1
- 或关键反馈仍聚焦“自动赚钱”而非纪律执行

停止（`no`）条件：

- interview_count >= 3 且 strong_count = 0 且 medium_count = 0
- 多数反馈明确不认可产品价值

---

## 6. 下一步唯一动作字段规范

`next_single_product_action` 必须为单一、可执行、可验收动作，例如：

- `clarify_ops_to_commands_narrative_in_demo_page_copy`
- `add_readonly_commands_timeline_explainer_block`
- `tighten_non_trading_disclaimer_visibility`

禁止写成多动作集合或模糊描述。

---

## 7. 与上游文档关系

- 候选人与联系状态来源：`PROJECT_ANCHOR_EARLY_DEMO_CONTACT_LOG_V1.md`
- 单场访谈细节来源：`PROJECT_ANCHOR_EARLY_DEMO_INTERVIEW_RECORD_V1.md`
- 招募边界与话术来源：`PROJECT_ANCHOR_EARLY_DEMO_RECRUITING_LIST_V1.md`

本文件只做汇总，不替代上游记录。

---

## 8. 禁止事项

- 不在本文件记录个人隐私
- 不用主观印象替代计数事实
- 不在一个周期内定义多个“下一步动作”
- 不把未访谈样本计入 strong/medium/weak

---

## 9. 回滚方式

如果未提交：

```bash
cd /Users/baolood/Projects/project-anchor
rm -f anchor-backend/docs/PROJECT_ANCHOR_EARLY_DEMO_FEEDBACK_SUMMARY_V1.md
git status --short
```

如果已提交：

```bash
cd /Users/baolood/Projects/project-anchor
git revert HEAD
```

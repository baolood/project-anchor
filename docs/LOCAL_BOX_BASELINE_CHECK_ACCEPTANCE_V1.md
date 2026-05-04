# LOCAL_BOX_BASELINE_CHECK_ACCEPTANCE_V1

## 0. 状态快照（与正文的关系）

- 本文 **立项时** 用于把「baseline check 写什么算验收通过」写成唯一门槛；下文 §1–§9 保留为 **当时** 的收口语义。
- **当前事实：** baseline check 已在仓库内以 **脚本 + CI** 兑现；运行与维护口径见 **`docs/LOCAL_BOX_BASELINE_SCRIPT_STATUS_V1.md`**、**`docs/LOCAL_BOX_BASELINE_WORKFLOW_RUN_EVIDENCE_V1.md`**；脚本与路径以 **`docs/LOCAL_BOX_BASELINE_CHECK_SCRIPT_SPEC_V1.md`** 与 **`scripts/check_local_box_baseline.sh`** 为准。若字句与实现不一致，以上述实现与 STATUS 为准。
- **「下一步」** 仍以 **`docs/LOCAL_BOX_NEXT_SINGLE_ACCEPTANCE_TARGET_V1.md`**（当前版）为准：**扩面须新立唯一目标**，不得默认继续本条主线。

## 1. 结论

- **`（历史 · 立项期）`** `local_box` 当时下一步只允许先定义 baseline check 的单一验收标准。
- **`（历史 · 立项期）`** 在本文件获批并落库前，不进入 `local_box/` 实现。

## 2. 目标对象

- 当前唯一验收对象：
  - `local_box baseline check`
- 当前阶段只回答：
  - baseline check 最小要检查什么
  - 以什么结果判定 PASS / FAIL
  - 失败时如何回滚或停止推进

## 3. 允许修改范围

- 当前轮次只允许：
  - 新增 `docs/LOCAL_BOX_BASELINE_CHECK_ACCEPTANCE_V1.md`
- 当前轮次不允许：
  - 修改 `local_box/`
  - 修改 `execution_service/`
  - 修改 `risk_engine/`
  - 修改 `shared/`
  - 修改 `cloud/`
  - 修改 `anchor-backend/`
  - 修改子模块
  - 新增并行 active 目标

## 4. baseline check 最小验收内容

- 至少必须能明确以下 3 件事：

1. **对象是否存在**
   - baseline check 对应的脚本 / 命令 / 入口是否明确存在
   - 不允许只停留在抽象描述

2. **输出是否可直接判断**
   - 结果必须可以直接区分 PASS / FAIL
   - 不允许依赖模糊解释或人工猜测

3. **失败后是否可停止推进**
   - 一旦 baseline check 不通过，必须有明确停止推进口径
   - 不允许 check 失败后继续进入 `local_box` 实现

## 5. PASS 条件

- baseline check 的目标入口明确
- baseline check 的 PASS / FAIL 判断标准明确
- baseline check 的失败停止口径明确
- 可以据此决定是否值得进入下一步最小实现

## 6. FAIL 条件

- 找不到明确入口
- 无法判断 PASS / FAIL
- 失败后仍无法决定是否停止推进
- 仍然需要并行修改多个目录才能成立

## 7. 回滚方法

- 若本轮仅新增本文档：
  - 删除 `docs/LOCAL_BOX_BASELINE_CHECK_ACCEPTANCE_V1.md`
- 不涉及代码回滚

## 8. 当前明确不做什么

- **`（历史 · 立项期）`** 不写 `local_box` 代码（**之后**已按单独任务入库最小 baseline 路径；见 §0）。
- **`（历史 · 立项期）`** 不补 baseline check 实现（**之后**已由 `scripts/check_local_box_baseline.sh` 与 CI 承担；见 §0）。
- 不改 compose / infra
- 不联动其它模块

## 9. 一句话判断

- `local_box` 只有在 baseline check 的入口、PASS/FAIL、失败停止口径都写死后，才允许进入下一步。

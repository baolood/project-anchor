# LOCAL_BOX_BASELINE_CHECK_CREATION_DECISION_V1

## 1. 结论

- 当前阶段对 `scripts/check_local_box_baseline.sh` 的唯一判断是：
  - **暂不允许直接创建脚本，先写死最小脚本职责与最小输出口径后，才允许进入创建。**

## 2. 前置事实

- `docs/LOCAL_BOX_BASELINE_CHECK_EXISTENCE_RESULT_V1.md` 已确认脚本不存在。
- `docs/LOCAL_BOX_BASELINE_CHECK_MISSING_SCRIPT_DISPOSITION_V1.md` 已确认当前不准直接补脚本。
- `docs/LOCAL_BOX_BASELINE_CHECK_CREATION_ACCEPTANCE_V1.md` 已写清创建门槛：
  - 职责单一
  - 入口明确
  - 结果可判
  - 失败可停

## 3. 当前判断依据

- 虽然创建门槛已被定义，
- 但“脚本若被创建时的最小职责”和“脚本最小输出口径”还没有被单独写死。
- 因此当前还不满足直接进入脚本创建阶段。

## 4. 当前明确禁止

- 不直接创建 `scripts/check_local_box_baseline.sh`
- 不修改 `local_box/`
- 不修改 `execution_service/`
- 不修改 `risk_engine/`
- 不修改 `shared/`
- 不修改 `cloud/`
- 不修改 `anchor-backend/`
- 不并行开启第二目标

## 5. 唯一下一目标

- 只允许新增 1 份文档：
  - `docs/LOCAL_BOX_BASELINE_CHECK_SCRIPT_SPEC_V1.md`
- 该文档必须写清：
  - 脚本的最小职责
  - 脚本的标准入口
  - 脚本 PASS 输出长什么样
  - 脚本 FAIL 输出长什么样
  - 脚本失败后如何停止推进

## 6. 为什么现在还不能创建

- 如果先创建脚本再补规格，主线会再次变成“先实现，后补口径”
- 当前 Project Anchor 要求：
  - 先定义
  - 再验收
  - 最后才允许最小实现

## 7. 回滚方法

- 若本轮仅新增本文档：
  - 删除 `docs/LOCAL_BOX_BASELINE_CHECK_CREATION_DECISION_V1.md`

## 8. 一句话判断

- 现在还没到创建 `check_local_box_baseline.sh` 的阶段；下一步只允许先把脚本规格写死。

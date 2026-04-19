# LOCAL_BOX_BASELINE_CHECK_MISSING_SCRIPT_DISPOSITION_V1

## 1. 结论

- `scripts/check_local_box_baseline.sh` 当前不存在。
- 因此 `local_box baseline check` 当前不允许进入执行验证阶段。
- 下一步唯一允许推进的方向，不是直接补脚本，而是先定义“是否创建该脚本”的单一验收门槛。

## 2. 当前事实来源

- `docs/LOCAL_BOX_BASELINE_CHECK_EXISTENCE_RESULT_V1.md` 已确认：
  - 文件不存在
  - 无可执行位
  - 头部不可读
- 以上事实已进入主线。

## 3. 当前明确禁止

- 不直接创建 `scripts/check_local_box_baseline.sh`
- 不修改 `local_box/`
- 不修改 `execution_service/`
- 不修改 `risk_engine/`
- 不修改 `shared/`
- 不修改 `cloud/`
- 不修改 `anchor-backend/`
- 不并行开启第二目标

## 4. 唯一下一目标

- 只允许新增 1 份文档：
  - `docs/LOCAL_BOX_BASELINE_CHECK_CREATION_ACCEPTANCE_V1.md`
- 该文档必须回答：
  - 是否值得创建 `scripts/check_local_box_baseline.sh`
  - 若创建，最小职责是什么
  - 若不创建，当前就此停止推进的条件是什么

## 5. 为什么不能直接补脚本

- 现阶段还没有写死“创建脚本”的单一验收目标
- 若直接补脚本，会再次跳过边界与验收，回到先实现后补解释的老问题
- 当前主线要求：先定义验收门槛，再允许最小实现

## 6. 当前唯一判断

- `local_box baseline check` 还停留在“对象缺失后的处理定义”阶段
- 未到实现阶段
- 未到执行验证阶段

## 7. 回滚方法

- 若本轮仅新增本文档：
  - 删除 `docs/LOCAL_BOX_BASELINE_CHECK_MISSING_SCRIPT_DISPOSITION_V1.md`

## 8. 一句话判断

- 现在唯一正确下一步，不是补 `check_local_box_baseline.sh`，而是先把“缺失后是否创建、按什么门槛创建”写死。

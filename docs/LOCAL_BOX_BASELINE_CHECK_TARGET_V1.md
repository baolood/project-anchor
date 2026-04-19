# LOCAL_BOX_BASELINE_CHECK_TARGET_V1

## 1. 结论

- `local_box baseline check` 当前只允许锁定 1 个唯一验收对象。
- 在该对象写死并落库前，不进入 `local_box/` 实现。

## 2. 前置事实

- `docs/LOCAL_BOX_BOUNDARY_AND_ACCEPTANCE_V1.md` 已锁定边界。
- `docs/LOCAL_BOX_NEXT_SINGLE_ACCEPTANCE_TARGET_V1.md` 已锁定下一唯一目标为 baseline check。
- `docs/LOCAL_BOX_BASELINE_CHECK_ACCEPTANCE_V1.md` 已锁定 baseline check 的验收框架。

## 3. 唯一验收对象

- 当前唯一验收对象写死为：
  - **`scripts/check_local_box_baseline.sh`**
- 当前阶段只围绕这个对象回答：
  - 它是否存在
  - 它是否可执行
  - 它是否能直接给出 PASS / FAIL

## 4. 为什么只选这个对象

- 它是最小、最直接、最容易验证的 baseline check 入口。
- 它比同时牵动 `local_box/`、`execution_service/`、`risk_engine/` 更可控。
- 它能把“是否值得进入 local_box 下一步”先收口成一个单点判断。

## 5. 当前明确不做什么

- 不修改 `scripts/check_local_box_baseline.sh`
- 不修改 `local_box/`
- 不修改 `execution_service/`
- 不修改 `risk_engine/`
- 不修改 `shared/`
- 不修改 `cloud/`
- 不修改 `anchor-backend/`
- 不并行选择第二个 baseline 对象

## 6. 下一轮唯一允许推进的内容

- 只新增一份文档：
  - `docs/LOCAL_BOX_BASELINE_CHECK_TARGET_ACCEPTANCE_V1.md`
- 该文档必须写清：
  - `scripts/check_local_box_baseline.sh` 的存在性检查方法
  - 执行方式
  - PASS 条件
  - FAIL 条件
  - 回滚方法

## 7. 一句话判断

- `local_box baseline check` 现在的唯一正确下一步，不是改脚本，而是先把唯一验收对象锁定为 `scripts/check_local_box_baseline.sh`。

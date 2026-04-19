# LOCAL_BOX_NEXT_SINGLE_ACCEPTANCE_TARGET_V1

## 1. 结论

- `local_box` 下一步只允许推进 1 个唯一验收目标。
- 在该目标获批并落库前，不进入 `local_box/` 实现。

## 2. 前置边界

- 以 `docs/LOCAL_BOX_BOUNDARY_AND_ACCEPTANCE_V1.md` 为准。
- 当前仍然：
  - 不改 `local_box/` 代码或配置
  - 不改 `execution_service/`
  - 不改 `risk_engine/`
  - 不改 `shared/`
  - 不改 `cloud/`
  - 不改 `anchor-backend/`
  - 不改子模块
  - 不并行开启第二目标

## 3. 唯一下一验收目标

- 只定义：
  - **新增 `docs/LOCAL_BOX_BASELINE_CHECK_ACCEPTANCE_V1.md`**
- 该文档的目标是：
  - 把 `local_box` 的最小 baseline check 对象、通过条件、失败条件、回滚方式写死
  - 为后续是否值得进入 `local_box` 实现提供唯一验收门槛

## 4. 为什么只选这个目标

- 这是当前最小、最稳、可验证的下一步
- 先锁定 baseline check 验收，才能避免后续 `local_box` 进入无边界实现
- 这一步只动文档，不会破坏现有主线稳定性

## 5. 当前明确不做什么

- 不新增 `local_box/` 代码
- 不改任何配置
- 不补测试
- 不联动其它目录
- 不把 `local_box` 扩写成完整新主线

## 6. 下一轮通过标准

- 必须只新增 1 份文档：
  - `docs/LOCAL_BOX_BASELINE_CHECK_ACCEPTANCE_V1.md`
- 必须写清：
  - 目标文件/路径
  - 允许修改范围
  - 禁止修改范围
  - PASS 条件
  - FAIL 条件
  - 回滚方法

## 7. 一句话判断

- `local_box` 现在的唯一正确下一步，不是写实现，而是先把 baseline check 的单一验收标准写死。

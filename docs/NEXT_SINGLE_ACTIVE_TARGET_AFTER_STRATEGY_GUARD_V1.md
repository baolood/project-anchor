# NEXT_SINGLE_ACTIVE_TARGET_AFTER_STRATEGY_GUARD_V1

## 1. 结论

- `domain_command_worker` strategy guard 主线已封板完成。
- 当前不得继续沿该主线进入第六刀。
- strategy guard 之后，必须重新定义新的唯一主线目标。

## 2. 当前边界

- 不再继续：
  - `domain_command_worker` strategy guard 第六刀
  - strategy guard 相关扩展实现
- 本轮不碰（指 **不对下列路径做代码或配置变更**；若 §4 需要，允许仅在 `docs/` 撰写与之相关的边界说明任务文档）：
  - `anchor-backend/app/workers/domain_command_worker.py`
  - `anchor-backend/app/risk/policy_engine.py`
  - `cloud/`
  - `execution_service/`
  - `local_box/`
  - `risk_engine/`
  - `shared/`
  - `anchor.db`
  - `test_*.py`
  - 子模块

## 3. 新主线选择规则

- 只能选 1 个目标
- 必须可验证、可回滚
- 必须不依赖 strategy guard 继续扩刀
- 必须先有验收标准，再进入实现

## 4. 当前唯一下一目标

- **文档先行、单刀**：下一唯一主线目标为新增 `docs/LOCAL_BOX_BOUNDARY_AND_ACCEPTANCE_V1.md`，写死 `local_box/` 的职责边界与 **单一** 验收标准；在该文档获批前，**不修改** `local_box/`（及 §2 所列其它路径）内任何代码或配置，不并行开启其它实验目录升格主线。

## 5. 本轮不做什么

- 不改代码
- 不提交 backend 实现
- 不推进实验目录
- 不开启新的并行线

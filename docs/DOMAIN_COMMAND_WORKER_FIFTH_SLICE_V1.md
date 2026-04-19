# DOMAIN_COMMAND_WORKER_FIFTH_SLICE_V1

## 1. 目标

- 本文档只回答一个问题：
- 在第四刀已落库的前提下，`domain_command_worker.py` 的第五刀唯一切片是什么

## 2. 前置事实

- 第一刀已落库：顶层 forbidden 字段守卫函数 `_strategy_v1_top_payload_forbidden_field`
- 第二刀已落库：bypass forbidden key 常量与最大深度常量
- 第三刀已落库：嵌套 bypass 探测纯函数与根入口薄包装
- 第四刀已落库：`_risk_guard` 顶部已接入 **`_strategy_v1_command_payload_nested_bypass`**（命中 **`NESTED_BYPASS_FORBIDDEN:{hit}`**）
- **当前缺口**：`_strategy_v1_top_payload_forbidden_field` **仍未在任何执行路径被调用**
- 第五刀必须只基于当前 `main`

## 3. 约束

- 不允许扩展到新的意图分支
- 不允许引入 `_STRATEGY_V1_INTENT_KINDS`
- 不允许补 imports
- 不允许整包推进 `domain_command_worker.py`
- 只允许 **1 处**逻辑扩展：**`_risk_guard` 函数体内** 增加 **顶层 forbidden** 的一次早退（与第四刀同属 **同一接线面**）
- 必须可单独验收、可单独回滚

## 4. 排除范围

- 不碰：
  - `anchor-backend/app/risk/policy_engine.py`
  - `cloud/`
  - `execution_service/`
  - `local_box/`
  - `risk_engine/`
  - `shared/`
  - `anchor-backend/docs/`
  - `anchor-backend/scripts/insert_order_command.py`
  - `anchor-backend/worker/WORKER_BOUNDARY_RULES.md`
  - `anchor.db`
  - `test_*.py`
  - 子模块

## 5. 第五刀唯一切片

- **接线位置（唯一）**：仍在 **`domain_worker_loop` 内的 `async def _risk_guard(cmd_type: str, payload: dict)`**——在 **当前第四刀 nested bypass 两段代码之前**（即 **整个 `_risk_guard` 函数体新的最顶端**）。
- **调用顺序（写死）**：
  1. **`top_hit = _strategy_v1_top_payload_forbidden_field(payload)`**
  2. 若 **`top_hit`** 真值：**`return (False, f"TOP_LEVEL_FORBIDDEN_FIELD:{top_hit}")`**
  3. **否则**再执行第四刀已落库的 **`hit = _strategy_v1_command_payload_nested_bypass(payload)`** / **`NESTED_BYPASS_FORBIDDEN`** 早退；
  4. **否则**落入原有 **`p = payload or {}`** 及后续 `notional` / `RiskPolicyEngine` / **`risk_guard`** 路径（**不改**其后任意逻辑）。
- **参数**：与第四刀一致，**直接传入 `payload`**（`_risk_guard` 形参已为 **`dict`**；若未来放宽类型，实现时可与第四刀同步改为 **`payload if isinstance(payload, dict) else {}`**，**本刀文档仍以「单参数 `payload`」为验收口径**）。
- **明确禁止（本刀不得同时做）**：
  - **不** 修改 **`while True`**、`runner.run_one()`、kill / heartbeat 等 **`domain_worker_loop`** 外层结构；
  - **不** 修改模块级 **第一～四刀** 已落库的 **常量区与 `def` 定义**（仅 **调用**已有函数）；
  - **不** 引入 **`_STRATEGY_V1_INTENT_KINDS`**、**不** 补 **import**；
  - **不** 重写 runner / 事件总线的错误模型（仅增加 **一道 `(False, reason)`** 早退字符串前缀 **`TOP_LEVEL_FORBIDDEN_FIELD:`**）。

## 6. 为什么先做这刀

- 顶层 forbidden 字段守卫函数已存在，但尚未真正接入主线
- 第五刀只做 `_risk_guard` 内的单点接线，是当前最小闭环
- 这样可让第一刀与第四刀在同一入口层形成 **「顶层键 → 嵌套 bypass → 原有风险」** 的稳定顺序

## 7. 本轮不做什么

- 不修改 `domain_command_worker.py`
- 不提交 backend 代码
- 不恢复旧 WIP
- 不更新子模块

## 8. 证据

- `/tmp/domain_command_worker_after_fourth_slice.py` — `git show HEAD:anchor-backend/app/workers/domain_command_worker.py` 导出（约 **881** 行）
- **`_risk_guard`** 当前形态（第四刀后）：约 **L738–748**，先 **nested bypass**，再 **`p = payload or {}`**（第五刀将把 **top payload** 检查插入其 **上方**）

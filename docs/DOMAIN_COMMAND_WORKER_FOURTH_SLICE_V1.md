# DOMAIN_COMMAND_WORKER_FOURTH_SLICE_V1

## 1. 目标

- 本文档只回答一个问题：
- 在第三刀已落库的前提下，`domain_command_worker.py` 的第四刀唯一切片是什么

## 2. 前置事实

- 第一刀已落库：顶层 forbidden 字段守卫（常量 + `_strategy_v1_top_payload_forbidden_field`）
- 第二刀已落库：bypass forbidden key 常量与最大深度常量
- 第三刀已落库：`_strategy_v1_nested_bypass_forbidden_scan` + `_strategy_v1_command_payload_nested_bypass`
- **当前 `main` 核查**：上述函数在 **`domain_command_worker.py` 内仍为「仅定义」**——**不存在**字面意义上的「已在运行的 strategy_v1 预检查链」同文件调用点；因此第四刀既是 **第一次把第三刀接入执行路径**，也是在 **现有 runner 契约下能拿到的最浅单点**
- 第四刀必须只基于当前 `main`

## 3. 约束

- 不允许扩展到新的意图分支（**不得**新增「仅 ORDER / 仅 standardized_strategy_request_v1」等分支作为本刀内容）
- 不允许引入 `_STRATEGY_V1_INTENT_KINDS`
- 不允许补 imports
- 不允许整包推进 `domain_command_worker.py`
- 只允许 **1 个接线点**、**1 次**对 `_strategy_v1_command_payload_nested_bypass` 的调用（实现上对应 **一道早退逻辑**，允许拆成 **2～4 行**：取 `dict` → 调用 → `if hit: return …`）
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

## 5. 第四刀唯一切片

- **接线位置（唯一）**：**`domain_worker_loop` 内部** 已存在的嵌套函数 **`async def _risk_guard(cmd_type: str, payload: dict)`**——在其函数体 **最顶端**（在 **`p = payload or {}`**、**`notional_usd`**、**`RiskPolicyEngine.evaluate_single_trade`** 等任一逻辑 **之前**）插入接入逻辑。
- **单次调用语义**：
  - `p = payload if isinstance(payload, dict) else {}`
  - `hit = _strategy_v1_command_payload_nested_bypass(p)`
  - 若 **`hit is not None`**：**`return (False, f"NESTED_BYPASS_FORBIDDEN:{hit}")`**（字符串前缀可依团队现有 `risk_guard_fn` 失败口径微调，但 **必须** 保持 **`(False, reason: str)`** 二元组形态，与当前 `_risk_guard` 其它失败返回 **一致**，**不得** 在本刀引入新的事件类型或改写 runner 契约）。
  - 若 **`hit is None`**：**原样落入** 原有 `_risk_guard` 函数后续逻辑（不改后续任意一行语义）。
- **明确禁止（本刀不得同时做）**：
  - **不** 在同一函数内接入 `_strategy_v1_top_payload_forbidden_field`（顶层 forbidden 接线列为 **后续独立切片**，避免第四刀范围膨胀；当前第一刀仍为「定义未调用」）。
  - **不** 修改 **`while True`**、`runner.run_one()`、`kill_switch`、**`heartbeat`** 等 **`domain_worker_loop`** 外层控制流（**仅** 允许改动 **`_risk_guard` 函数体开头**）。
  - **不** 修改第一刀～第三刀已落库的 **常量区** 与 **`def` 定义**（**只读调用** `p` / `hit`）。
  - **不** 引入 `_STRATEGY_V1_INTENT_KINDS`、**不** 补 **import**。

## 6. 为什么先做这刀

- 第三刀函数已存在，但还未真正接入执行路径
- 第四刀只做“单点调用”，是最小可验证的闭环
- 这样可以把“函数能力存在”推进到“主线第一次真正使用”，同时避免扩展成整段业务改造

## 7. 本轮不做什么

- 不修改 `domain_command_worker.py`
- 不提交 backend 代码
- 不恢复旧 WIP
- 不更新子模块

## 8. 证据

- `/tmp/domain_command_worker_after_third_slice.py` — `git show HEAD:anchor-backend/app/workers/domain_command_worker.py` 导出（约 **878** 行；**`rg` 显示** `_strategy_v1_*` **仅出现于模块常量/函数定义区**，**未** 在 `domain_worker_loop` / `_risk_guard` 内被引用）
- **`_risk_guard`** 大致位置：见当前 `main` 中 **`domain_worker_loop` 内** **`async def _risk_guard`**（约在 **L738–745** 段，具体行号随版本略变）

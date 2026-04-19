# DOMAIN_COMMAND_WORKER_SECOND_SLICE_V1

## 1. 目标

- 本文档只回答一个问题：
- 在第一刀已落库、mega WIP 无恢复来源的前提下，`domain_command_worker.py` 的第二刀唯一切片是什么

## 2. 前置事实

- 第一刀已落库
- `docs/DOMAIN_COMMAND_WORKER_FIRST_SLICE_V1.md` 已进入主线事实源
- `docs/DOMAIN_COMMAND_WORKER_WIP_RECOVERY_SOURCE_CHECK_V1.md` 已确认 mega WIP 无恢复来源
- 第二刀必须只基于当前 `main`

## 3. 约束

- 不允许按旧 mega WIP 继续推进
- 不允许整包提交 `domain_command_worker.py`
- 只允许定义 1 个最小切片
- 该切片必须可单独验收、可单独回滚
- 不得夹带其它 backend 文件

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

## 5. 第二刀唯一切片

- **位置**：紧接在 **`_strategy_v1_top_payload_forbidden_field` 函数体结束（`return None` 之后）** 与 **`async def domain_worker_loop` 之前**。
- **仅包含以下符号与注释（顺序与 mega 草案一致，但只到此为止）**：
  1. 注释行 **`# codex-active-013: explicit high-risk *bypass / override* names (nested scan only uses this set).`**
  2. **`_STRATEGY_V1_FORBIDDEN_BYPASS_KEYS`** `frozenset` 整块；
  3. **`_STRATEGY_V1_FORBIDDEN_BYPASS_KEYS_LOWER`**；
  4. **`_STRATEGY_V1_NESTED_FORBIDDEN_SCAN_MAX_DEPTH`**（`int(os.getenv("STRATEGY_REQUEST_V1_NESTED_FORBIDDEN_MAX_DEPTH", "12"))`）。
- **明确不包含（一律留到第三刀及以后）**：
  - **`_STRATEGY_V1_INTENT_KINDS`** 及之后所有 intent / qty / side / signing / HMAC / JSON 规范与辅助函数；
  - **任何对 `domain_worker_loop`、`_pick_one_domain`、runner 的调用点修改**；
  - **文件头** 新增 **`hashlib` / `hmac` / `math` / `datetime` / `typing.Tuple`**（本切片只依赖已有 **`os`**，与第一刀一致）。
- **原因**：（1）与第一刀同属 **「禁止面数据常量」**，体量小、边界在源码里一行即可划清（下一行即 intent kinds）；（2）**不引入新 import、不进入主循环**，审查与回滚成本极低；（3）为后续「嵌套扫描实现」提供 **唯一键集与深度上限** 事实输入，避免第二刀直接跨入大体量递归/签名逻辑。

## 6. 本轮不做什么

- 不修改 `domain_command_worker.py`
- 不提交 backend 代码
- 不恢复任何旧 WIP
- 不更新子模块

## 7. 证据

- `/tmp/domain_command_worker_current_main.py` — `git show HEAD:anchor-backend/app/workers/domain_command_worker.py` 导出（约 **835** 行；第一刀块约 **639–681** 行，其后直接进入 **`domain_worker_loop`**）
- 工作区 **`anchor-backend/app/workers/domain_command_worker.py`** 与 **`HEAD` 一致**（本核查未改文件；可用 `git diff HEAD -- anchor-backend/app/workers/domain_command_worker.py` 验证为空）

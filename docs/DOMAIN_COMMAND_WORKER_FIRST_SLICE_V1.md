# DOMAIN_COMMAND_WORKER_FIRST_SLICE_V1

## 1. 目标

- 本文档只回答一个问题：
- `anchor-backend/app/workers/domain_command_worker.py` 的下一步第一刀，具体切哪一小段

## 2. 约束

- 不允许整包提交整个 `domain_command_worker.py`
- 只允许选 1 个最小片段
- 该片段必须可单独验收、可单独回滚
- 不得同时夹带其它 backend 文件

## 3. 候选切片原则

- 优先体量最小
- 优先边界最清晰
- 优先不牵连其它目录 / 文件
- 优先能用日志、返回值、状态语义做验收

## 4. 明确排除

- 不碰实验目录：
  - `cloud/`
  - `execution_service/`
  - `local_box/`
  - `risk_engine/`
  - `shared/`
- 不碰：
  - `anchor-backend/docs/`
  - `anchor-backend/scripts/insert_order_command.py`
  - `anchor-backend/worker/WORKER_BOUNDARY_RULES.md`
  - `anchor.db`
  - `test_*.py`
  - 子模块

## 5. 第一刀唯一切片

- **位置**：紧接在 **`async def _pick_one_domain` 函数体结束（最后一个 `}`）之后**，到 **`# codex-active-013` 与 `_STRATEGY_V1_FORBIDDEN_BYPASS_KEYS` 之前**（不含该注释及后续任意行）。
- **包含内容（仅此一段）**：
  1. **`_STRATEGY_V1_FORBIDDEN_KEYS`** 整块 `frozenset`；
  2. **`FORBIDDEN_FIELDS`**、**`_FORBIDDEN_FIELDS_LOWER`** 及紧邻的 **STANDARDIZED_STRATEGY_REQUEST_FORBIDDEN_FIELD** 说明注释；
  3. **`_strategy_v1_top_payload_forbidden_field`** 函数全文（纯函数：扫描顶层 `command_payload` 键名，命中 `FORBIDDEN_FIELDS` 则返回原始键名，否则 `None`）。
- **明确不包含（一律留到第二刀及以后）**：
  - 自 **`_STRATEGY_V1_FORBIDDEN_BYPASS_KEYS`** 起的 nested bypass 扫描、深度 env、以及后续 intent / qty / signing / HMAC 等全部新增符号；
  - **`domain_worker_loop` 及拾取路径**上对该批符号的调用与行为变更（当前 diff 第三处 `@@` hunk）；
  - **文件头** diff 中的 **`import hashlib` / `hmac` / `math`**、**`from datetime import …`**、**`typing.Tuple`**：本切片内**无引用**，第一刀若一并提交易触发未使用 import / 与后续签名刀强耦合，故**推迟到与「需用这些模块的代码」同一刀**再提交。
- **原因（为何先切这段）**：（1）在整段 **~1500 行** 插入中，这是**唯一不依赖后续 helper**、边界在 diff 里肉眼可裁的**自洽子系统**；（2）验收可做**纯单元**：构造 `command_payload`，断言对 `exchange`/`api_key` 等键返回对应键名、对干净 payload 返回 `None`；（3）与 **bypass 嵌套扫描、签名字节、worker 主循环** 解耦，回滚时只删这一刀即可，不牵动执行主路径。

## 6. 本轮不做什么

- 不修改 `domain_command_worker.py`
- 不提交 backend 代码
- 不恢复实验目录
- 不更新子模块

## 7. 证据

- `/tmp/domain_command_worker.diff`（约 1511 行；结构为 **3 个 `@@` hunk**：文件头 import、`_pick_one_domain` 后大段插入、`domain_worker_loop` 处修改）

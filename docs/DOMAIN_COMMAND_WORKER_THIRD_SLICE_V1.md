# DOMAIN_COMMAND_WORKER_THIRD_SLICE_V1

## 1. 目标

- 本文档只回答一个问题：
- 在第二刀已落库的前提下，`domain_command_worker.py` 的第三刀唯一切片是什么

## 2. 前置事实

- 第一刀已落库：顶层 forbidden 字段守卫（`_STRATEGY_V1_FORBIDDEN_KEYS` / `FORBIDDEN_FIELDS` / `_strategy_v1_top_payload_forbidden_field`）
- 第二刀已落库：bypass 名称常量、小写派生集、嵌套扫描最大深度（`_STRATEGY_V1_FORBIDDEN_BYPASS_KEYS` / `_STRATEGY_V1_FORBIDDEN_BYPASS_KEYS_LOWER` / `_STRATEGY_V1_NESTED_FORBIDDEN_SCAN_MAX_DEPTH`）
- 当前仍不得按旧 mega WIP 推进
- 第三刀必须只基于当前 `main`

## 3. 约束

- 不允许直接改 `domain_worker_loop`
- 不允许引入 `_STRATEGY_V1_INTENT_KINDS` 及之后逻辑
- 不允许补文件头 imports
- 不允许整包推进 `domain_command_worker.py`
- 只允许定义 1 个最小切片（语义上为「嵌套 bypass 扫描」这一单元；实现上允许 **一个递归核心 + 一个对 `dict` 根入口的薄包装**，须同一提交、同一审查边界）
- 该切片必须可单独验收、可单独回滚

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

## 5. 第三刀唯一切片

- **插入位置**：紧接在 **`_STRATEGY_V1_NESTED_FORBIDDEN_SCAN_MAX_DEPTH` 赋值行之后**、**`async def domain_worker_loop` 之前**（与第二刀文档同一「常量区底部 / 主循环顶部」缝隙）。
- **允许新增（仅下列语义，不得扩张）**：
  1. **递归核心（必选）**：私有函数，建议命名为 **`_strategy_v1_nested_bypass_forbidden_scan(obj: Any, depth: int) -> Optional[str]`**（名称实现时可微调，须保持 **模块私有**）。
     - **深度**：若 **`depth > _STRATEGY_V1_NESTED_FORBIDDEN_SCAN_MAX_DEPTH`**，立即 **`return None`**（不再下探）。
     - **dict**：遍历键；对 **`str`** 键若 **`key.lower() in _STRATEGY_V1_FORBIDDEN_BYPASS_KEYS_LOWER`**，**立即返回该键的 wire 形式**（即 `key` 本身，保留大小写）。
     - **递归**：对每个 **值** 以 **`depth + 1`** 递归；若值为 **`list` / `tuple`**，对元素同样递归。
     - **其它类型**：不展开（**不**对 `str` 内容做子串扫描，避免范围爆炸）。
  2. **根入口薄包装（可选，与核心同一刀）**：**`_strategy_v1_command_payload_nested_bypass(command_payload: Dict[str, Any]) -> Optional[str]`**，体内仅 **`return _strategy_v1_nested_bypass_forbidden_scan(command_payload, 0)`**（或等价一行）；**不得**在此包装内引入 intent / signing / DB / asyncio。
- **明确禁止（第三刀内一律不得出现）**：
  - **`_STRATEGY_V1_INTENT_KINDS`** 及之后任意符号；
  - **修改** 已有第一刀、第二刀 **常量或第一刀、第二刀已存在函数** 的语义（仅允许在其 **下方追加** 新 `def`）；
  - **`domain_worker_loop` / `_pick_one_domain` / `DomainCommandRunner` 接线**；
  - **文件头** 新增 **`import`** / **`from … import`**（仅允许使用文件顶部 **已存在** 的 `typing.Any`、`Dict`、`Optional` 等）。

## 6. 为什么先做这刀

- 这是当前最小、最稳定的下一步
- 先把扫描能力本身独立成纯函数，后续接入点才有明确边界
- 这样可避免把「函数定义」和「业务接线」混成一刀

## 7. 本轮不做什么

- 不修改 `domain_command_worker.py`
- 不提交 backend 代码
- 不恢复旧 WIP
- 不更新子模块

## 8. 证据

- `/tmp/domain_command_worker_after_second_slice.py` — `git show HEAD:anchor-backend/app/workers/domain_command_worker.py` 导出（约 **852** 行；第二刀块约 **684–698** 行，其后一行空行即 **`domain_worker_loop`**）
- 工作区 **`anchor-backend/app/workers/domain_command_worker.py`** 与 **`HEAD` 一致**（本步骤未改代码；可用 `git diff HEAD -- …/domain_command_worker.py` 验证为空）

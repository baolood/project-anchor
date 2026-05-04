# SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1

## 1. 结论

- **`shared/schemas.py`** 当前仍是父仓库 **未跟踪草稿**（与其余实验目录同列，但语义权重不同）。
- **当前**：不对 **`shared/`** 做删除、不做目录/文件迁移，且 **不在未立项条件下直接并入主线**。
- **统一状态：** **`pending_decision`**。
- **建议策略（冻结口径）：** **保留待立项**——将本文件视为 **`cloud` / `execution_service` / `risk_engine` / `local_box` 的类型契约枢纽**；不得按「普通零散 pending 文件」顺手删或顺手 `git add`。

---

## 2. 当前文件清单

- **`shared/schemas.py`**

**说明：** **`shared/__pycache__/`** 下的 **`.pyc`** 为 **本地 Python 运行时产物**，**不是**本条文档的交付物组成部分；本轮 **不处理** `__pycache__`，也不得将其纳入提交素材。

---

## 3. 用途摘要

**`shared/schemas.py`** 是一份 **草稿级共享类型模块**：

- 使用 **`dataclass`**、**`Enum`** 以及若干 **id 生成器**；
- **`StrategyIntent`**：策略意图载荷；
- **`NormalizedCommand`**：规范化后的指令形态；
- **`Stage` / `StageResult`**：阶段流水线语义；
- **`ExecutionTicket` / `ExecutionResult`**：执行票据与执行结果；
- **`ExecMode` / `Status`**：执行模式与状态枚举（含阶段性 **禁用 LIVE** 的注释语义）；
- **`Event`**：审计事件载荷。

其目的：**在并行实验骨架中**对齐「**策略意图 → 规范化指令 → 阶段流水线 → 执行票据/结果 → 审计事件**」相关的 **数据结构契约**。

---

## 4. 依赖关系（按消费方）

- **`cloud/strategy_api/server.py`**：依赖 **`StrategyIntent`**（`/publish` 解析）。
- **`execution_service/`**（`executor.py`、`server.py`、`verifier.py`）：依赖 **`ExecutionTicket`**、**`ExecMode`**、**`Status`**、**`ExecutionResult`** 等。
- **`risk_engine/client.py`**：依赖 **`ExecutionTicket`**。
- **`local_box/`**：**已入库**的多个 Python 文件广泛 **`from shared.schemas import …`**（含 runner、normalize、risk、policy、gate、control、audit 等路径语义）。
- **`docs/archive/manual_smoke/test_*.py`**（父仓已归档的手工 smoke 脚本）：依赖 **`shared.schemas`** 中的类型。

---

## 5. 与当前主线关系

- 与 **`commands_domain`**（**anchor-backend** 域指令主链）**无直接关系**。
- 与 **`local_box` baseline**（**`scripts/check_local_box_baseline.sh`** + 已入库最小 **`local_box/`** 路径 + GitHub Actions）**无直接验收关系**——baseline **当前不验证** **`shared` 是否可 import**、也不验证 **模块级类型可用性**。
- 与 **`local_box` 已入库实现**存在 **强耦合**：大量 **`from shared.schemas import …`** 使 **`shared/schemas.py` 在运行/导入层面成为事实依赖**。
- **隐含缺口（必须显式承认）：** 即便 **baseline CI 绿**，也 **不能**用「baseline 已过」**掩盖**「**干净 clone 仅检出已跟踪树时，可能仍缺未跟踪的 `shared/`**」这类 **import/契约风险**——须由 **单独立项**决定是把 **`shared` 正式入库**、还是 **解除/内联/搬迁** `local_box` 侧 import。

---

## 6. 当前禁止动作

- **`git add shared/`**：**禁止**在未单列任务立项下将枢纽草稿整体纳入版本控制。
- **删除或移动 `shared/` 目录树：** **禁止**在未授权任务下执行。
- **`__pycache__` 入库**：**禁止**。
- **修改 `.gitignore`**：**本轮**不得擅自用忽略规则「刷掉」风险而不改契约叙事。
- **单独将 `shared/schemas.py` 固化成「已封板正式契约」：** **禁止**仅凭口头或默认合并；须 **文档化所有权、兼容策略、破坏性变更门槛**。
- **在未处理 `local_box` 已入库 import 关系之前，不得归档或删除 `shared/`：** 须与搬迁/内联/入库方案同批立项。
- **将 `shared/` 与 `cloud` / `execution_service` / `risk_engine` 的处理目标在未立项下混提并线：** **禁止**。

---

## 7. 后续处理规则

- 若要处理 **`shared/`**，必须先 **新唯一立项**。
- 立项时必须先裁决：**`shared.schemas` 是否正式成为本仓库层级契约（以及版本边界）**。
- 必须说明：**`local_box` 已入库 import** 是否与 **`shared` 入库/搬迁/内联方案同一步切换**。
- 必须说明：**`cloud` / `execution_service` / `risk_engine`** 草稿是否跟随同一契约线与迁移路径。
- 必须定义：**schema 所有权**、**兼容策略**、**破坏性变更约束**、**验收**与 **回滚**。
- **未立项前**：维持 **`pending_decision`**。

---

## 8. 验收口径（针对「新增本决策记录」这一轮）

- 本轮在父仓库内 **只允许新增**：**`docs/SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1.md`**。
- **`git status`** 中 **`shared/`** 仍应保持 **未跟踪**。
- 不出现 **`shared/`** 被 **暂存 / 删除 / 移动**；不出现 **`__pycache__`** 入库；**不改 **`.gitignore`**。
- **不改 `local_box` 源代码**（本条任务边界）。

---

## 9. 回滚方法

- 删除本文件 **`docs/SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1.md`** 即可撤回本条「决策口径」的文字层冻结。
- 回滚 **不影响**：`shared/` 草稿、`local_box`、`cloud`、`execution_service`、`risk_engine`、`anchor-backend`、`anchor-console` 子模块等业务树内容。

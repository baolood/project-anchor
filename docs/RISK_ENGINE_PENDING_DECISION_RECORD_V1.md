# RISK_ENGINE_PENDING_DECISION_RECORD_V1

## 1. 结论

- **`risk_engine/client.py`** 当前仍是父仓库 **未跟踪草稿**。
- **当前**：不对 **`risk_engine/`** 做删除、不做目录/文件迁移，并 **不在未立项条件下直接并入主线**。
- **统一状态：** **`pending_decision`**。
- **建议策略（冻结口径）：** **保留待立项**。
- **语义纠正：** **`risk_engine/client.py` 当下不是独立的 risk 计算或策略引擎**，而是 **`execution_service` 的 thin HTTP client（草稿级编排壳）**；目录名易造成误解，必须以本文档口径为准。

---

## 2. 当前文件清单

- **`risk_engine/client.py`**

**说明：** **`risk_engine/__pycache__/`** 下的 **`.pyc`** 为 **本地 Python 运行时产物**，**不是**本条文档的交付物组成部分；本轮 **不处理** `__pycache__`，也不得将其纳入提交素材。

---

## 3. 用途摘要

- 使用 **`EXECUTION_SERVICE_URL`**，默认 **`http://127.0.0.1:9001`**。
- **`send_ticket`**：调用 **`POST /execute`**（相对上述 base URL）。
- **`get_receipt`**：调用 **`GET /receipt/{ticket_id}`**。
- 请求头使用 **`X-EXECUTION-KEY-ID`** 与 **`X-EXECUTION-KEY`**。
- 相关环境变量：**`EXECUTION_SERVICE_URL`**、**`EXECUTION_SHARED_KEY_ID`**、**`EXECUTION_SHARED_KEY`**。
- **未正确设置密钥**时，服务端可能返回 **`403`**（与 **`execution_service/server.py`** 的边界语义一致）。
- **当前文件不包含**独立的 risk 模型、风控规则计算或并行评估引擎逻辑。

---

## 4. 依赖关系

- **`risk_engine/client.py`** 依赖 **`shared.schemas.ExecutionTicket`**（类型与载荷形态）。
- 与 **`execution_service/server.py`** 在 **`9001`**、**`/execute`**、**`/receipt/<ticket_id>`** 路径上构成 **草稿级契约关系**。
- **Header 鉴权字段**与 **`execution_service/server.py`** **配套定义**。
- 若动 **`risk_engine/client.py`**：必须与 **`SHARED_SCHEMAS`、`EXECUTION_SERVICE`** 侧的 pending/立项决策 **对齐**，**禁止**单列「只管 client」而把 **`shared`/服务器**割裂。

---

## 5. 与当前主线关系

- 与 **`commands_domain`**（**anchor-backend** 域指令主链）**无直接关系**。
- 与 **`local_box` baseline**（**`scripts/check_local_box_baseline.sh`** + 已入库最小 **`local_box/`** + CI）**无直接关系**。
- **不参与** **`scripts/check_local_box_baseline.sh`**。
- **未立项前**：不得把本文件解释为 **正式 risk 引擎**、也不得解释为 **已与主线绑定的 execution client SDK**。

---

## 6. 当前禁止动作

- **`git add risk_engine/`**：**禁止**在未单列任务立项下将草稿整体纳入版本控制。
- **删除或移动 `risk_engine/` 目录树：** **禁止**在未授权任务下执行。
- **`__pycache__` 入库**：**禁止**。
- **修改 `.gitignore`**：**本轮**不得擅自改写忽略策略以粉饰风险。
- **单独将 `risk_engine/client.py` 并入主线：** **禁止**。
- **`cloud` / `execution_service` / `shared` 草稿**在未立项下联批处理：**禁止**套用「顺手一起 `git add`」。
- **借此推进 `local_box` 扩面：** **禁止**。

---

## 7. 后续处理规则

- 若要处理 **`risk_engine/`**，必须先 **新唯一立项**。
- 立项必须先选：**归档 / 删除 / 升格为正式 client（或更名搬迁）** 之一为主线（可多阶段，须写明）。
- 必须说明：**`shared.schemas`/`ExecutionTicket` 依赖**如何版本化或与契约库对齐。
- 必须说明：**`execution_service` 路由、Header、ENV、receipt 语义**的兼容策略与破坏性变更口径。
- 必须定义 **验收** 与 **回滚**。
- **未立项前**：维持 **`pending_decision`**。

---

## 8. 验收口径（针对「新增本决策记录」这一轮）

- 本轮在父仓库内 **只允许新增**：**`docs/RISK_ENGINE_PENDING_DECISION_RECORD_V1.md`**。
- **`git status`** 中 **`risk_engine/`** 仍应保持 **未跟踪**。
- 不出现 **`risk_engine/`** **暂存 / 删除 / 移动**；不出现 **`__pycache__`** 入库；**不改 `.gitignore`**。
- **不改 `shared/`、`execution_service/` 源代码**（本条任务边界）。

---

## 9. 回滚方法

- 删除本文件 **`docs/RISK_ENGINE_PENDING_DECISION_RECORD_V1.md`** 即可撤回本条「决策口径」的文字层冻结。
- 回滚 **不影响**：`risk_engine/` 草稿、`shared`、`execution_service`、`cloud`、`local_box`、`anchor-backend`、`anchor-console` 子模块等业务树内容。

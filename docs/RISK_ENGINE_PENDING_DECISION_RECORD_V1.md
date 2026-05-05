# RISK_ENGINE_PENDING_DECISION_RECORD_V1

## 1. 结论

- **原**父仓 **`risk_engine/client.py`**：**物理形态**已 **按 §9 归档入库**（跟踪副本 **`docs/archive/risk_engine_draft/client.py`**），**不再**作为 **`git ls-files --others --exclude-standard`** 下的 **`risk_engine/*.py`** 未跟踪条目残留。
- **语义纠正（仍有效）：** 该草稿 **不是**独立 risk 模型或规则引擎，而是 **`execution_service` 的 thin HTTP client**；目录名 **`risk_engine`** **易误导**——归档段保留此口径。
- **升格为正式 SDK / 更名搬迁：** 须 **重新唯一立项**。

---

## 2. 当前文件清单

### 2.1 归档跟踪路径

- **`docs/archive/risk_engine_draft/client.py`**

### 2.2 父仓顶层 **`risk_engine/`**

- **不应再**以 **未跟踪 **`client.py`** 草稿**形态出现；若重建 **`risk_engine/`** 实验树，须 **单列立项**。**`__pycache__/`** **不得**入库。

---

## 3. 用途摘要（归档稿）

- **`EXECUTION_SERVICE_URL`**（默认 **`http://127.0.0.1:9001`**）、**`send_ticket`**（**`POST /execute`**）、**`get_receipt`**（**`GET /receipt/{id}`**）。
- 请求头：**`X-EXECUTION-KEY-ID`**、**`X-EXECUTION-KEY`**；与 **`docs/archive/execution_service_draft/…/server.py`** 草稿 **配套**。
- **依赖 **`shared.schemas.ExecutionTicket`**：** 在 **Repo 根为 **`PYTHONPATH`** 前缀** 且 **`shared/`** 已跟踪时 **可 import**。

---

## 4. 依赖关系

- **`shared.schemas`**（**`shared/schemas.py`** 已跟踪）。
- **`execution_service`** 归档段（**`docs/archive/execution_service_draft/…`**）。

---

## 5. 当前禁止动作

- **`git add risk_engine/`** 整树 **一把梭**：**禁止**在未立项下执行。
- **删除 §9 归档跟踪文件**：**禁止**在未授权任务下执行。
- **把本 client 冒充正式 risk 引擎：** **禁止**。

---

## 6. 后续处理规则

- 升格/重命名/并入 SDK：**须单列立项** + **与 `shared`/`execution_service` 契约对齐说明**。

---

## 7. 验收口径（历史首轮）

- 首轮 **只允许新增** **`docs/RISK_ENGINE_PENDING_DECISION_RECORD_V1.md`**。

---

## 8. 回滚方法

- 删除 **`docs/RISK_ENGINE_PENDING_DECISION_RECORD_V1.md`** 仅撤回 **文字口径**层。

---

## 9. 归档状态更新

- **跟踪路径：** **`docs/archive/risk_engine_draft/client.py`**
- **例提交：** **`6ee8365`** **`feat(shared): track schemas package; archive risk_engine draft client`**
- **禁止**：借本条 **顺带**宣称 **`execution_service` 归档段**已升格为 **生产可运维服务**（簇级隔离与 **`EXECUTION_SERVICE`** 记录 **§9** 一致）。

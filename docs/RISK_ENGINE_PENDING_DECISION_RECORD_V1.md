# RISK_ENGINE_PENDING_DECISION_RECORD_V1

## 1. 结论

- **`risk_engine/client.py`**（及 **`risk_engine/__init__.py`**）为父仓 **跟踪对象**，供 **`local_box.runner`** 等路径 **`from risk_engine.client import …`** 使用。
- **语义纠正（冻结）：** 该模块 **不是**独立 risk 模型或规则引擎，而是 **`execution_service` 草稿 HTTP 客户端**（目录名 **`risk_engine`** 易误导，以本文为准）。
- **升格为正式 SDK / 更名 / 迁入 **`local_box`****：须 **单列立项**。

---

## 2. 当前文件清单（跟踪）

- **`risk_engine/__init__.py`**
- **`risk_engine/client.py`**

**说明：** **`risk_engine/__pycache__/`** **不得**入库。

---

## 3. 用途摘要

- **`EXECUTION_SERVICE_URL`**（默认 **`http://127.0.0.1:9001`**）、**`send_ticket`**（**`POST /execute`**）、**`get_receipt`**（**`GET /receipt/{id}`**）。
- 请求头：**`X-EXECUTION-KEY-ID`**、**`X-EXECUTION-KEY`**；与 **`docs/archive/execution_service_draft/…/server.py`** 草稿 **配套**。
- **依赖：** **`shared.schemas.ExecutionTicket`**。

---

## 4. 依赖关系

- **`shared.schemas`**（**`shared/schemas.py`** 已跟踪）。
- **`execution_service`** **归档段**（**`docs/archive/execution_service_draft/…`**）描述的服务边界。

---

## 5. 与当前主线关系

- 与 **`commands_domain`** **无直接关系**。
- 与 **`local_box` baseline** CI：**无直接验收绑定**；**`local_box/runner.py`** 存在 **`from risk_engine.client import …`** —— **删除本包前须同步改写 **`local_box`**。**

---

## 6. 当前禁止动作

- **`git add risk_engine/`** **一把梭**（未写清白名单立项）：**禁止**。
- **`__pycache__` 入库**：**禁止**。
- **把本 client 冒充正式 risk 引擎：** **禁止**。
- **在未改写 **`local_box`** import 前删除本跟踪路径：** **禁止**。

---

## 7. 后续处理规则

- 更名/迁入 **`local_box`** / 升格 SDK：**须单列立项** + **与 `shared`/`execution_service` 契约对齐**。

---

## 8. 验收口径（历史首轮）

- 首轮 **只允许新增** **`docs/RISK_ENGINE_PENDING_DECISION_RECORD_V1.md`**。

---

## 9. 回滚方法

- 删除 **`docs/RISK_ENGINE_PENDING_DECISION_RECORD_V1.md`** 仅撤回 **文字口径**层。

---

## 10. 跟踪锚点（曾误归档副本的纠正）

- **曾短暂入库：** **`docs/archive/risk_engine_draft/client.py`**（例 **`6ee8365`** 批次）—— **已从 Git 树移除**（**`8164c0a`** 批次完成 **`git rm`**），避免与 **`risk_engine/client.py`** **双源**；**唯一 SSOT** 为 **`risk_engine/client.py`**。
- **纠正提交：** **`183a011`** **`fix(risk_engine): restore tracked client for local_box imports`**
- **禁止**：借本条宣称 **`execution_service` 归档段**已升格为 **生产可运维服务**。

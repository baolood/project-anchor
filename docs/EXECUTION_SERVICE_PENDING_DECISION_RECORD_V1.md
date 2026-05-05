# EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1

## 1. 结论

- **原**父仓顶层 **`execution_service/*.py`** 实验草稿：**物理形态**已 **按 §9 归档入库**（跟踪副本位于 **`docs/archive/execution_service_draft/execution_service/…`**），**不再**作为 **`git ls-files --others --exclude-standard`** 下的 **`execution_service/`** 顶层未跟踪条目残留。
- **当前（归档段语义）：** 归档源码仍属 **历史实验占位**（Flask、`shared.schemas`、`local_box.audit.event_store`、`verifier` 内示例级 **`SECRET`**）；**升格为可运维正式服务**须 **重新唯一立项**。**归档入库 ≠ execution 已成正式运行时栈**。
- **`shared/`**（父仓 **`schemas.py`** 仍为 **pending 未跟踪**）与 **`local_box`** 已入库段落：**不讲**归档段在当前父仓状态下「可开箱跑通」，亦 **不讲**与安全相关的 **`SECRET`/共享密钥** 已升格为正式方案。
- **建议：** 若要恢复 **`execution_service/`** 顶树或与 **`risk_engine`/策略云**联动，须在立项中重写 **拓扑、密钥、契约与验收**。

---

## 2. 当前文件清单

### 2.1 归档跟踪路径（ **`docs/archive/execution_service_draft/execution_service/`** ，见 §9）

- **`__init__.py`**（占位包锚点）
- **`executor.py`**
- **`server.py`**
- **`verifier.py`**

### 2.2 父仓顶层 **`execution_service/`**

- **不应再**以 **未跟踪 `*.py`** 草稿形态出现；若以 **新建顶树**卷土重来，视同 **下一轮实验**，须 **单列 **`git status`**/`git add` 立项**。**`__pycache__/`** **不得**入库。

---

## 3. 用途摘要

- **`executor.py`**：**`execute_simulate`** / **`execute_testnet`**；后者为占位 **TESTNET-MOCK**。
- **`server.py`**：**Flask**；**`EXECUTION_SHARED_KEYS`**；**`/execute`** 验门票与签、**禁止 `LIVE`**；写 **`local_box.audit.event_store`** 回执；**`/receipt/<id>`** 读取。
- **`verifier.py`**：**SHA256** 玩具签验；内含 **硬编码 `SECRET`**（**示例级**，**禁止冒充生产密钥叙事**）。

---

## 4. 与当前主线关系

- 与 **`commands_domain`** **无直接关系**。
- 与 **`local_box` baseline** CI **无直接关系**；与 **`local_box.audit.event_store`** **归档稿内仍存在 import 耦合**。
- **`shared.schemas`** **强依赖**；**父仓 **`shared/schemas.py`** pending** 状态下，归档段 **不满足**完整类型/模块解析假设。

---

## 5. 当前禁止动作

- **`git add execution_service/`**（指 **新建的**顶层整棵草稿树）：**禁止**在未立项下 **一把梭**。
- **删除 §9 归档跟踪文件**：**禁止**在未授权任务下执行。
- **`__pycache__` 入库**：**禁止**。
- **在未立项下联批 **`shared` / `risk_engine` / `cloud`**：** **禁止**。
- **`SECRET`/`EXECUTION_SHARED_KEYS` 升格为不经评审的生产方案**：**禁止**借归档完成宣称。

---

## 6. 后续处理规则

- 升格或恢复 **`execution_service` 顶树**：须 **单列立项**。
- 须写明：**密钥**、**签算法**、**禁 LIVE**、**回执边界**、`shared`/契约、`local_box` 耦合可否保留。

---

## 7. 验收口径（历史首轮）

- 首轮 **只允许新增** **`docs/EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1.md`**。

---

## 8. 回滚方法

- 删除 **`docs/EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1.md`** 仅撤回本条 **文字口径**冻结层。

---

## 9. 归档状态更新

- **跟踪前缀：** **`docs/archive/execution_service_draft/execution_service/`**
- **`PYTHONPATH`**：若在无父仓源码树辅助下尝试导入，典型需将 **`docs/archive/execution_service_draft`** 与 **Repo 根目录**一并纳入 **`sys.path`**（以便解析 **`execution_service`** 与 **`shared`/`local_box`** —— **`shared`** 若仍 **`pending`** 则 **不完整**）。
- **依赖重申：** **`verifier.py`** 内常量 **`SECRET`** 为 **教学/草稿**残留；**`server.py`** 依赖 **`EXECUTION_SHARED_KEYS`** 环境拼接。
- **`shared/`**：归档段 **仍会** **`from shared.schemas import …`** —— **`shared/schemas.py`** **未升格前**，**不讲**本条归档可单机跑通。
- **后续**：升格正式服务必须 **另行契约 + 立项**。**禁止**：借本条 **顺带收口 **`risk_engine`/`shared`** 其它 pending。**（簇级隔离。）

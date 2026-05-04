# EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1

## 1. 结论

- **`execution_service/`** 当前属于父仓库中的 **未跟踪实验草稿组**。
- **当前**：不对 **`execution_service/`** 做删除、不做目录/文件迁移，并 **不入主线提交**。
- **统一状态：** **`pending_decision`**。
- **建议策略（冻结口径）：** **保留待立项**——含执行边界、验签、禁 **`LIVE`**、回执 API 等设计草图；在未定义正式密钥与契约前 **不得**当成可合并主线的执行面。

---

## 2. 当前文件清单

本记录覆盖的草稿源路径：

- **`execution_service/executor.py`**
- **`execution_service/server.py`**
- **`execution_service/verifier.py`**

**说明：** **`execution_service/__pycache__/`** 下的 **`.pyc`** 为 **本地 Python 运行时产物**，**不是**本条文档的交付物组成部分；本轮 **不处理** `__pycache__`，也不得将其作为提交素材。

---

## 3. 用途摘要

- **`execution_service/executor.py`**
  - 提供 **`execute_simulate`** 与 **`execute_testnet`**。
  - **`execute_simulate`**：生成 **模拟成交**，返回 **`ExecutionResult`**（**`SIMULATED`** 语义）。
  - **`execute_testnet`**：当前为 **`TESTNET-MOCK`**，**未**接真实交易所，仅返回占位结果。
- **`execution_service/server.py`**
  - **Flask** **执行占位服务**；默认监听 **`127.0.0.1:9001`**（可通过环境变量覆盖 host/port）。
  - **`GET /health`**：返回服务名与 **共享密钥 id** 等 **边界信息**。
  - **`POST /execute`**：
    - 校验请求头 **`X-EXECUTION-KEY-ID`** / **`X-EXECUTION-KEY`**（与 **`EXECUTION_SHARED_KEYS`** 配置匹配）。
    - 解析 **`ExecutionTicket`**，**`verify_ticket` 验签**。
    - **禁止 LIVE 模式**（`ExecMode.LIVE`）。
    - 按 **`ExecMode`** 调用 **`execute_simulate`** 或 **`execute_testnet`**。
    - 调用 **`local_box.audit.event_store`** 写入 **execution receipt**（**`save_execution_receipt`**）。
  - **`GET /receipt/<ticket_id>`**：通过 **`get_execution_receipt`** **读取** execution receipt。
- **`execution_service/verifier.py`**
  - 使用 **简化 · 基于 SHA256** 的 **签名 / 验签**（**`sign_ticket` / `verify_ticket`**）。
  - **当前存在硬编码 `SECRET`（示例级）**，**不适合**在未立项条件下 **并入主线** 或冒充 **正式密钥方案**。

---

## 4. 与当前主线关系

- 与 **`commands_domain`**（**anchor-backend** 域指令主链）**无直接关系**。
- 与 **`local_box` baseline**（**`scripts/check_local_box_baseline.sh`** + 已入库最小 **`local_box/`** + CI）**无直接关系**。
- **`server.py`** 与 **`local_box.audit.event_store`** **存在耦合**（回执读写）；**不得**在未立项前把该耦合解释成 **`local_box` 主线已验收的扩面结论**。
- **`execution_service/`** **强依赖** **`shared.schemas`**（类型与载荷模型）。
- **未立项前**：不得把本草稿组解释为 **已并入 `local_box` 主线** 或 **已封板的 execution 主线**。

---

## 5. 当前禁止动作

- **`git add execution_service/`**：**禁止**在未单列任务立项下将整个草稿目录纳入版本控制。
- **删除或移动 `execution_service/` 目录树：** **禁止**在本轮或未授权任务下执行。
- **`__pycache__` 入库**：**禁止**。
- **修改 `.gitignore`**：**本轮**不得擅自调整忽略策略以「消灭噪音」为名改变风险边界。
- **与 **`shared` / `risk_engine` / `cloud`** 的 pending 草稿**联批处理：**禁止**。
- **借此推进 **`local_box` 扩面****：**禁止**。
- **把硬编码 **`SECRET`** 当作正式密钥方案**：**禁止**。

---

## 6. 后续处理规则

- 若要处理 **`execution_service/`**，必须先 **新唯一立项**。
- 立项时必须先选：**归档 / 删除 / 升格为真实长期服务** 之一为主路线（可多阶段，须写清）。
- 必须说明：**`shared.schemas` 依赖**如何版本化或搬迁。
- 必须说明：**`local_box.audit.event_store` 耦合**是否保留、接口契约、以及回执存储是否独立服务化。
- 必须说明：**密钥管理**、**签名算法**、**禁 LIVE** 策略、**receipt API** 的 **正式安全边界**（含轮换、审计、误用防护）。
- 必须写明 **验收** 与 **回滚**。
- **未立项前**：维持 **`pending_decision`**。

---

## 7. 验收口径（针对「新增本决策记录」这一轮）

- 本轮在父仓库内 **只允许新增**：**`docs/EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1.md`**。
- **`git status`** 中 **`execution_service/`** 仍应保持 **未跟踪**。
- 不出现 **`execution_service/`** 被 **暂存 / 删除 / 移动**；不出现 **`__pycache__`** 入库；**不改 **`.gitignore`**。

---

## 8. 回滚方法

- 删除本文件 **`docs/EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1.md`** 即可撤回本条「决策口径」的文字层冻结。
- 回滚 **不影响**：`execution_service/` 草稿、`local_box`、`shared`、`risk_engine`、`cloud`、`anchor-backend`、`anchor-console` 子模块等业务树内容。

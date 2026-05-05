# PARENT_UNTRACKED_PENDING_DECISION_TABLE_V1

## 1. 结论

- 父仓 **未跟踪路径**曾以 **初版 13 项**快照登记（见 §2 附：**历史对齐**）；现阶段 **`git ls-files --others --exclude-standard` 口径下，本表 §2.1 所维护的 **`pending_decision`** 未跟踪清单为 **0**（见 §2 **当前权威清单**）。
- **对「未来新出现的」未跟踪实验路径**：在未新唯一立项前，不执行删除，不归档实体，不并入主线，不对其做未授权 `git add`。
- **后续**：仍须 **新唯一立项** 后 **逐项或按目录组** 处理；**不得**因 §2.1 暂时为空而默认 **可 `git add .` 清屏**。

---

## 2. 当前权威清单

### 2.1 仍为未跟踪（计数 **0**；与 `git ls-files --others --exclude-standard` 一致，`anchor.db` 等已忽略项不在此列）

**（空）** —— 与 **`git ls-files --others --exclude-standard`** 核对：**无**仍属本表曾登记 **13 项演进链** 的 **残留未跟踪源码路径**。

### 2.2 附：初版 13 项快照 → 当前对齐（台账用）

| 原 §2 条目（初版） | 现状态 |
|-------------------|--------|
| `anchor-backend/docs/DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md` | **已升格跟踪**（例：`fcc76b3` **`docs: add domain command validation dev usage`**） |
| `anchor-backend/scripts/insert_order_command.py` | **已升格跟踪**（例：**`9c20d55`** **`fix(scripts): require ANCHOR_DB_* env …`**）；口令仅 **`ANCHOR_*`** 环境变量注入，必填 **`ANCHOR_DB_PASSWORD`**，见 **`ANCHOR_BACKEND`** **§11** |
| `anchor-backend/worker/WORKER_BOUNDARY_RULES.md` | **已归档入库** **`docs/archive/anchor_backend_draft/worker/WORKER_BOUNDARY_RULES.md`**（见 `ANCHOR_BACKEND` 记录 **§2.2／§10**） |
| `cloud/strategy_api/server.py`、`cloud/strategy_store/versions.py` | **已归档入库**（跟踪路径见 `docs/CLOUD_PENDING_DECISION_RECORD_V1.md` §9 **`docs/archive/cloud_draft/…`**） |
| `execution_service/executor.py`、`execution_service/server.py`、`execution_service/verifier.py` | **已归档入库**（例：**`10ccfad`** **`docs(archive): move execution_service draft…`**；路径 **`docs/archive/execution_service_draft/execution_service/…`**，见 **`EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1.md`** **§9**） |
| `risk_engine/client.py` | **已升格跟踪** **`risk_engine/client.py`**（例：**`6ee8365`** 起 **`shared`** 同批；**`docs/archive/risk_engine_draft/client.py`** 为 **误双源已删**；纠正见 **`fix(risk_engine): restore tracked client for local_box imports`** 与 **`RISK_ENGINE`** **§10**） |
| `shared/schemas.py`（及 **`shared/__init__.py`**） | **已升格跟踪**（例：**`6ee8365`**；见 **`SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1.md`** **§10**） |
| 根目录 `test_ack_semantics.py`、`test_cloud_publish.py`、`test_execution_service.py` | 已迁入 `docs/archive/manual_smoke/` 并跟踪 |
| **§2.1 当前** | **无 **`pending_decision`** 未跟踪残留**（上表历史条目均已落入 §2.2 各行 **现态**） |

---

## 3. 分类状态

**§2.1 当前无行可填。** 若 **`git status`** 再次出现 **`??`** 实验源码路径：**仍须**按 **簇级 **`PENDING_DECISION_RECORD_V1`** 与唯一立项** 处理；**禁止**顺手 **`git add .`**。

---

## 4. 当前禁止动作

- **`git clean`**：**不得**对工作区或未跟踪清单执行清理类命令。
- **`rm`**：**不得**对 **新出现**的未跟踪实验路径或整条实验目录树做破坏性删除（除非下一轮单独立项明确授权）。
- **批量 `git add`**：**不得**在未单列任务立项下把多块实验路径一次性混入暂存。
- **混入 unrelated commit**：不得把本表覆盖路径与主线需求无关的改动捆在同一变更集。
- **借清屏推进 `local_box` 扩面**：清屏与子模块/`local_box`**不得**隐含联动；**`local_box` 扩面**仍须在 **单独唯一立项**后进行。
- **修改 `.gitignore`**：**本轮与本表语义下**：不得为了解决「看得见未跟踪」而擅自改忽略规则抵消风险（若确需改动，必须在 **新唯一立项**中写明动机、范围与验收）。

---

## 5. 后续处理规则

- **一轮只处理**：**一个路径**，或预先写清的一个 **目录组**（须有独立文档批准）。
- **每轮必选其一**：保留 / 归档 / 删除 / 并入主线（四选一或可组合为归档+删除等，但必须写清）。
- **每轮必须**：写明 **验收口径**与 **回滚方法**。
- **未立项前**：若 §2.1 **未来**再出现登记项，仍维持在 **`pending_decision`**，直至立项处置。

---

## 6. 验收口径

- **本轮**在父仓库内 **只允许新增**：`docs/PARENT_UNTRACKED_PENDING_DECISION_TABLE_V1.md`。
- **提交核对**：在仅暂存本文档的理想情况下，`git diff --cached --name-only` 应 **只列出**本文档路径。
- **禁止**：在未立项下 **批量**引入 **新**未跟踪实验路径并混入无关 commit。

---

## 7. 回滚方法

- 删除本文件 **`docs/PARENT_UNTRACKED_PENDING_DECISION_TABLE_V1.md`** 即可撤回「决策表本轮」的记录层变更。
- 回滚 **不影响**：已入库代码、`scripts`、`local_box` baseline、`anchor-console` 子模块、GitHub Actions workflow、未跟踪文件的磁盘内容——它们保持原状，仅撤回本表所提供的冻结口径文档。

---

## 8. 第二阶段覆盖索引

**与 §2 的关系：** §2.2 保留 **立项当时 13 条路径**快照与 **现态**对照。§2.1 与下表为 **`git ls-files --others --exclude-standard`** 下 **仍存在的未跟踪**与 **已落库 `PENDING_DECISION_RECORD_V1`** 的 **索引对齐**。

### 8.1 当前剩余未跟踪文件（0 个）

与 **`git ls-files --others --exclude-standard`** 口径一致（**2026-04 收口**）：**（空）** —— 本表曾跟踪的 **13 项演进链** 中 **源码/草稿路径**均已 **升格或归档**或已 **在 §2.2 对齐**；**不宣称**父仓 **不存在任何**其它 **`??`**（例如个人本地 scratch），**仅宣称**本条 **登记口径下** **无残留**。

### 8.2 五簇与五份决策记录（5 个簇；均已落库）

| 簇 | 对应 `PENDING_DECISION_RECORD_V1`（已跟踪） |
|----|---------------------------------------------|
| **`anchor-backend/`** | `docs/ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1.md` |
| **`cloud/`** | `docs/CLOUD_PENDING_DECISION_RECORD_V1.md` |
| **`execution_service/`** | `docs/EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1.md` |
| **`risk_engine/`** | `docs/RISK_ENGINE_PENDING_DECISION_RECORD_V1.md` |
| **`shared/`** | `docs/SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1.md` |

### 8.3 归档与覆盖结论

- **`anchor-backend/docs/DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`** 已于父仓 **`anchor-backend/docs/`** 下 **升格跟踪**（例提交 **`fcc76b3`**），**不再**出现在 **`git ls-files --others --exclude-standard`**（仍属 **`anchor-backend`** 治理叙事：`docs/ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1.md`）。
- **`anchor-backend/scripts/insert_order_command.py`** 已 **升格跟踪**（**仅用环境变量**承载 DB 口令；例提交 **`9c20d55`**，见 **`ANCHOR_BACKEND`** §11）。
- **`anchor-backend/worker/WORKER_BOUNDARY_RULES.md`** 已由未跟踪草稿 **归档入库**至 **`docs/archive/anchor_backend_draft/worker/WORKER_BOUNDARY_RULES.md`**，**不应再**残留在 **`anchor-backend/worker/`** 未跟踪路径上。
- 根目录三文件 **`test_ack_semantics.py`**、**`test_cloud_publish.py`**、**`test_execution_service.py`** 已迁入 **`docs/archive/manual_smoke/`** 并在父仓 **跟踪**；此三文件 **不再**出现在 **`--others --exclude-standard`** 中。
- **`cloud/strategy_*` 源草稿**按 **`CLOUD`** 记录 **§9** 归档至 **`docs/archive/cloud_draft/…`** 并已跟踪；**原顶层 `cloud/`** 不作为 **pending 未跟踪顶簇**残留在清单中。
- **`execution_service/*.py`** 已由 **`execution_service/`** 顶层未跟踪草稿 **归档入库**至 **`docs/archive/execution_service_draft/execution_service/…`**（例提交 **`10ccfad`**，见 **`EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1.md`** **§9**）；**顶层 `execution_service/`** **不应再**附带未跟踪 **`*.py`**。
- **`shared/schemas.py`**（及 **`shared/__init__.py`**）已 **升格跟踪**（例提交 **`6ee8365`**），见 **`SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1.md`** **§10**。
- **`risk_engine/client.py`** 现为 **跟踪** **`risk_engine/`** 包内 **SSOT**（**`local_box`** 硬依赖 **`from risk_engine.client`**）；曾误入库 **`docs/archive/risk_engine_draft/client.py`** 已 **删除**，见 **`RISK_ENGINE_PENDING_DECISION_RECORD_V1.md`** **§10**。
- **当前**在 **`--others --exclude-standard`** 语义下，**不存在**「**有未跟踪源文件簇却无任何 `PENDING_DECISION_RECORD_V1` 覆盖**」的额外缺口——**5 簇 ↔ 5 份记录**一一对应；**§2.1 清单为空**表示 **本表登记项已收口**。

### 8.4 下一阶段动作边界（封口径）

- **每次只选一个簇**单独立项：只做 **归档 / 删除 / 升格入库** 之一为主路线（须 **验收 + 回滚**）。
- **禁止 **`git add .`**。**
- **禁止**在同一 commit **跨簇混提** pending 草稿。
- **禁止**在未单列任务授权下对实验树执行 **`git clean`**。（与 §4 一脉相承，本节为第二阶段收口后的显式复述。）
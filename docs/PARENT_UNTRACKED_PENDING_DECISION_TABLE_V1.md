# PARENT_UNTRACKED_PENDING_DECISION_TABLE_V1

## 1. 结论

- 父仓 **未跟踪路径**已通过 **只读盘点**收口；本表登记 **13 个**未跟踪路径（见 §2）。
- **当前**：不执行删除，不归档，不并入主线，不对上述路径做任何 `git add`。
- **所有 13 项**的统一状态：**`pending_decision`**。
- **后续**：必须 **新唯一立项** 后 **逐项或按目录组** 处理；未立项前不得推进清屏或多线并行。

---

## 2. 当前权威清单

以下为 **本轮冻结**父仓 **未跟踪路径**全集（计数 **13**；与 `git ls-files --others --exclude-standard` 口径一致，`anchor.db` 等已忽略项不在此列）：

1. `anchor-backend/docs/DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`
2. `anchor-backend/scripts/insert_order_command.py`
3. `anchor-backend/worker/WORKER_BOUNDARY_RULES.md`
4. `cloud/strategy_api/server.py`
5. `cloud/strategy_store/versions.py`
6. `execution_service/executor.py`
7. `execution_service/server.py`
8. `execution_service/verifier.py`
9. `risk_engine/client.py`
10. `shared/schemas.py`
11. `test_ack_semantics.py`
12. `test_cloud_publish.py`
13. `test_execution_service.py`

---

## 3. 分类状态

| path | group | current_status | allowed_next_action | forbidden_action |
|------|-------|----------------|---------------------|------------------|
| `anchor-backend/docs/DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md` | `anchor-backend/docs` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `anchor-backend/scripts/insert_order_command.py` | `anchor-backend/scripts` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `anchor-backend/worker/WORKER_BOUNDARY_RULES.md` | `anchor-backend/worker` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `cloud/strategy_api/server.py` | `cloud` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `cloud/strategy_store/versions.py` | `cloud` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `execution_service/executor.py` | `execution_service` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `execution_service/server.py` | `execution_service` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `execution_service/verifier.py` | `execution_service` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `risk_engine/client.py` | `risk_engine` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `shared/schemas.py` | `shared` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `test_ack_semantics.py` | `repo-root` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `test_cloud_publish.py` | `repo-root` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |
| `test_execution_service.py` | `repo-root` | `pending_decision` | 新唯一立项后再处理 | 不得顺手 git add / git clean / rm / 并入主线 |

---

## 4. 当前禁止动作

- **`git clean`**：**不得**对工作区或未跟踪清单执行清理类命令。
- **`rm`**：**不得**对上述 13 个路径或整条实验目录树做破坏性删除。
- **批量 `git add`**：**不得**在未单列任务立项下把多块实验路径一次性混入暂存。
- **混入 unrelated commit**：不得把本表覆盖路径与主线需求无关的改动捆在同一变更集。
- **借清屏推进 `local_box` 扩面**：清屏与子模块/`local_box`**不得**隐含联动；**`local_box` 扩面**仍须在 **单独唯一立项**后进行。
- **修改 `.gitignore`**：**本轮与本表语义下**：不得为了解决「看得见未跟踪」而擅自改忽略规则抵消风险（若确需改动，必须在 **新唯一立项**中写明动机、范围与验收）。

---

## 5. 后续处理规则

- **一轮只处理**：**一个路径**，或预先写清的一个 **目录组**（须有独立文档批准）。
- **每轮必选其一**：保留 / 归档 / 删除 / 并入主线（四选一或可组合为归档+删除等，但必须写清）。
- **每轮必须**：写明 **验收口径**与 **回滚方法**。
- **未立项前**：所有登记项维持在 **`pending_decision`**。

---

## 6. 验收口径

- **本轮**在父仓库内 **只允许新增**：`docs/PARENT_UNTRACKED_PENDING_DECISION_TABLE_V1.md`。
- **提交核对**：在仅暂存本文档的理想情况下，`git diff --cached --name-only` 应 **只列出**本文档路径；**未跟踪的 13 个路径不参与暂存**，仍应保持 `git status` 的 `??` 形态不变。
- **禁止**：新增、删除、移动 **§2 所列 13 个路径**的任何实体文件或目录层级（除非下一轮单独立项明确授权）。

---

## 7. 回滚方法

- 删除本文件 **`docs/PARENT_UNTRACKED_PENDING_DECISION_TABLE_V1.md`** 即可撤回「决策表本轮」的记录层变更。
- 回滚 **不影响**：已入库代码、`scripts`、`local_box` baseline、`anchor-console` 子模块、GitHub Actions workflow、§2 所列未跟踪文件的磁盘内容——它们保持原状，仅撤回本表所提供的冻结口径文档。

---

## 8. 第二阶段覆盖索引

**与 §2 的关系：** §2 为立项当时 **13 条路径**快照（含当时在仓库根的 **3** 个 `test_*.py`）。本节记录 **已将根目录 `test_*.py` 迁入 `docs/archive/manual_smoke/` 并入库** 之后，**`git ls-files --others --exclude-standard`** 下 **仍存在的未跟踪源代码/草稿** 与 **已落库 `PENDING_DECISION_RECORD_V1`** 的 **索引对齐**事实。

### 8.1 当前剩余未跟踪文件（10 个）

与 **`git ls-files --others --exclude-standard`** 口径一致（**2026-04 复核**）：

1. `anchor-backend/docs/DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`
2. `anchor-backend/scripts/insert_order_command.py`
3. `anchor-backend/worker/WORKER_BOUNDARY_RULES.md`
4. `cloud/strategy_api/server.py`
5. `cloud/strategy_store/versions.py`
6. `execution_service/executor.py`
7. `execution_service/server.py`
8. `execution_service/verifier.py`
9. `risk_engine/client.py`
10. `shared/schemas.py`

### 8.2 五簇与五份决策记录（5 个簇；均已落库）

| 簇 | 对应 `PENDING_DECISION_RECORD_V1`（已跟踪） |
|----|---------------------------------------------|
| **`anchor-backend/`** | `docs/ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1.md` |
| **`cloud/`** | `docs/CLOUD_PENDING_DECISION_RECORD_V1.md` |
| **`execution_service/`** | `docs/EXECUTION_SERVICE_PENDING_DECISION_RECORD_V1.md` |
| **`risk_engine/`** | `docs/RISK_ENGINE_PENDING_DECISION_RECORD_V1.md` |
| **`shared/`** | `docs/SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1.md` |

### 8.3 归档与覆盖结论

- 根目录三文件 **`test_ack_semantics.py`**、**`test_cloud_publish.py`**、**`test_execution_service.py`** 已迁入 **`docs/archive/manual_smoke/`** 并在父仓 **跟踪**（见提交历史 **`docs: archive manual smoke test drafts`** 一类记录）；此三文件 **不再**出现在 **`git ls-files --others --exclude-standard`** 中。
- **当前**在 **`--others --exclude-standard`** 语义下，**不存在**「**有未跟踪源文件簇却无任何 `PENDING_DECISION_RECORD_V1` 覆盖**」的额外缺口——**5 簇 ↔ 5 份记录**一一对应。

### 8.4 下一阶段动作边界（封口径）

- **每次只选一个簇**单独立项：只做 **归档 / 删除 / 升格入库** 之一为主路线（须 **验收 + 回滚**）。
- **禁止 **`git add .`**。**
- **禁止**在同一 commit **跨簇混提** pending 草稿。
- **禁止**在未单列任务授权下对实验树执行 **`git clean`**。（与 §4 一脉相承，本节为第二阶段收口后的显式复述。）

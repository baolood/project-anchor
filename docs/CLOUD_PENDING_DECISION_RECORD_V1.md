# CLOUD_PENDING_DECISION_RECORD_V1

## 1. 结论

- **原**父仓顶层 **`cloud/strategy_api/server.py`、`cloud/strategy_store/versions.py`** 实验草稿：**物理形态**已 **按 §9 归档入库**（跟踪副本位于 **`docs/archive/cloud_draft/…`**），**不再**作为 **`git ls-files --others --exclude-standard`** 下的 **`cloud/` 顶簇未跟踪条目**残留。
- **当前（归档段语义）：** 归档源码仍属 **`pending_decision`** 类别的 **历史实验留痕**，**升格为可运维正式服务**须 **重新唯一立项**；**删除/搬迁归档段**亦须单列任务。
- **建议策略：** 维持 **§9 归档语义**；若未来恢复 **`cloud/`** 布局或升格服务，须在立项中重写 **拓扑、验收与 `shared` 依赖边界**。
- **`shared/`** 仍为父仓 **pending 未跟踪**契约枢纽之一（详见 **`SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1`**）：**不讲**归档段在本仓库当前状态下「可单机跑通」。

---

## 2. 当前文件清单

### 2.1 归档跟踪路径（ **`docs/archive/cloud_draft/…`** ，见 §9）

- **`strategy_api/server.py`**
- **`strategy_store/versions.py`**

**说明：** 历史上 **`cloud/strategy_store/__pycache__/versions.cpython-312.pyc`** 等为 **本地 Python 运行时产物**，**不是**交付物组成部分；**不处理 **`__pycache__`** 入库**。

### 2.2 原顶层 **`cloud/strategy_*`**

- **不再**列入父仓 **`--others`** pending 清点；若以 **新目录树**再次出现顶层 **`cloud/`** 草稿，视同 **新一轮实验**，须 **单列立项**后方可 `git add`。

---

## 3. 用途摘要

- **`strategy_api/server.py`：** **Flask** 占位服务。
  - 提供 **`GET /health`**。
  - 提供 **`POST /publish`**。
  - **`/publish`** 使用 **`shared.schemas.StrategyIntent`** 解析请求体。
  - 调用 **`strategy_store.versions.is_allowed_version`**（**`PYTHONPATH`/包布局**以实现为准）做 **策略版本白名单**校验。
  - 校验通过后，将 intent **转发**到 **`http://127.0.0.1:9002/run-intent`**（假定下游 **`local_box`** HTTP 在 **9002**）。
  - 默认 **`app.run(port=9003)`**（服务监听 **9003**）。
- **`strategy_store/versions.py`：** 维护 **`ALLOWED_STRATEGY_VERSIONS`** 集合，并提供 **`is_allowed_version(version)`**。

---

## 4. 与当前主线关系

- 与 **`commands_domain`**（**anchor-backend** 域指令 HTTP / worker / risk 主链）**无直接关系**。
- 与 **`local_box` baseline**（**`scripts/check_local_box_baseline.sh`** + 已入库最小 **`local_box/`** 对象 + GitHub Actions）**无直接关系**。
- 语义上属于 **并行实验骨架**：**Cloud Flask `9003` → 假定 `local_box` `9002`（`/run-intent`）**。
- **归档后**：不得以「文件已入库」隐含 **`local_box` HTTP 面值扩面**或多服务编排并线——仍须立项。

---

## 5. 当前禁止动作

- **`git add cloud/`**：**禁止**在未单列任务立项下将 **新建的**顶层 **`cloud/`** 草稿树整簇纳入提交（归档段已由 **`docs/archive/cloud_draft/…`** 表达）。
- **删除 §9 归档跟踪文件**：**禁止**在未授权任务下执行。
- **`__pycache__` 入库**：**禁止**。
- **修改 `.gitignore`**：**不得以**粉饰未决风险为目的擅自调整忽略策略。
- **与 `execution_service` / `risk_engine` / `shared` 的 pending 草稿**捆在一起处理：**禁止**在未立项下联批决策。
- **与 **`local_box` 扩面**混做一单**：**禁止**。

---

## 6. 后续处理规则

- 若要 **升格归档段为服务**或 **恢复 **`cloud/`** 布局**：必须先 **新唯一立项**。
- 立项须先选：**继续仅归档留痕 / 删除归档段 / 升格为真实长期服务** 之一为主线（可多阶段，须写清）。
- 必须同步说明：**`shared` 依赖边界**如何处理，以及 **`9002`/`local_box` HTTP 假设**是否保留或替换。
- 必须写明 **验收** 与 **回滚**。

---

## 7. 验收口径（针对「新增本决策记录」上一轮）

- 历史轮次在父仓库内 **只允许新增**：**`docs/CLOUD_PENDING_DECISION_RECORD_V1.md`**。
- **归档后**：**`git ls-files --others --exclude-standard`** **不应再**列出原 **`cloud/strategy_api`、`cloud/strategy_store`** 两份源路径（与 §9、`PARENT_UNTRACKED_PENDING_DECISION_TABLE_V1.md` §8 一致）。
- 不出现：**未立项下整棵 `git add cloud/`**、**`__pycache__` 入库**、或对 **`.gitignore`** 的非授权修改。

---

## 8. 回滚方法

- 删除本文件 **`docs/CLOUD_PENDING_DECISION_RECORD_V1.md`** 即可撤回本条「决策口径」的文字层冻结。
- 回滚 **不影响**：归档段、`local_box`、`shared`、`execution_service`、`risk_engine`、`anchor-backend`、`anchor-console` 子模块等业务树内容——它们保持原物理状态与其它任务节奏。

---

## 9. 归档状态更新

- **`cloud/` 草稿源文件**已 **归档并入库（父仓库跟踪）**，不再散落在原 **`cloud/`** 未跟踪目录下。
- **新路径（跟踪对象）：**
  - **`docs/archive/cloud_draft/strategy_api/server.py`**
  - **`docs/archive/cloud_draft/strategy_store/versions.py`**
- 原 **`cloud/`** 目录：不再作为 **`git status`** 下的 **未跟踪 pending 顶层目录**出现（与工作区现状一致）。
- **归档语义**：上述文件仍属 **历史实验草稿**留痕；**不代表**运行时栈已收口为可运维 **正式服务**。
- **shared/ 仍为 pending**：归档代码仍含 **`from shared.schemas …`** —— **不宣称可运行**：**不宣称 **`cloud`** 归档片段在本仓库状态下「可单机跑通」**，亦 **不宣称**已解除对 **`shared.schemas`** 的依赖。
- **升级口径**：**归档入库 ≠ **`cloud`** 已升格为正式服务**；须 **单独契约、部署叙事与验收**，并 **新立项**后再宣称。
- **后续**：若要恢复源码布局或与 **`local_box` HTTP** 联调升格，须先 **唯一立项**。
- **禁止**：借本条顺带处理 **`shared/`**、**`execution_service/`**、**`risk_engine/`**、**`anchor-backend/`** pending 簇。（簇级隔离。）

# CLOUD_PENDING_DECISION_RECORD_V1

## 1. 结论

- **`cloud/`** 当前属于父仓库中的 **未跟踪实验草稿组**（与 `commands_domain`、`local_box` baseline CI 验收入口均不同轨）。
- **当前**：不对 **`cloud/`** 做删除、不做目录/文件迁移、并 **不入主线提交**。
- **统一状态：** **`pending_decision`**。
- **建议策略（冻结口径）：** **保留待立项**——避免在未定义拓扑与验收前误删或误并入 **`main`**。

---

## 2. 当前文件清单

本记录覆盖的草稿源路径：

- **`cloud/strategy_api/server.py`**
- **`cloud/strategy_store/versions.py`**

**说明：** **`cloud/strategy_store/__pycache__/versions.cpython-312.pyc`** 为 **本地 Python 运行时产物**，**不是**本条文档的交付物组成部分；本轮 **不处理 `__pycache__`**，也不得将其作为提交素材。

---

## 3. 用途摘要

- **`cloud/strategy_api/server.py`**：**Flask** 占位服务。
  - 提供 **`GET /health`**。
  - 提供 **`POST /publish`**。
  - **`/publish`** 使用 **`shared.schemas.StrategyIntent`** 解析请求体。
  - 调用 **`cloud.strategy_store.versions.is_allowed_version`** 做 **策略版本白名单**校验。
  - 校验通过后，将 intent **转发**到 **`http://127.0.0.1:9002/run-intent`**（假定下游 **`local_box`** HTTP 在 **9002**）。
  - 默认 **`app.run(port=9003)`**（服务监听 **9003**）。
- **`cloud/strategy_store/versions.py`**：维护 **`ALLOWED_STRATEGY_VERSIONS`** 集合，并提供 **`is_allowed_version(version)`**。

---

## 4. 与当前主线关系

- 与 **`commands_domain`**（**anchor-backend** 域指令 HTTP / worker / risk 主链）**无直接关系**。
- 与 **`local_box` baseline**（**`scripts/check_local_box_baseline.sh`** + 已入库最小 **`local_box/`** 对象 + GitHub Actions）**无直接关系**。
- 语义上属于 **并行实验骨架**：**Cloud Flask `9003` → 假定 `local_box` `9002`（`/run-intent`）**。
- **未立项前**：不得借本骨架 **隐式推进 `local_box` HTTP 面值扩面**或多服务编排并线。

---

## 5. 当前禁止动作

- **`git add cloud/`**：**禁止**在未单列任务立项下将整个草稿目录纳入版本控制。
- **删除 **`cloud/`**、**移动 **`cloud/`**：**禁止**。
- **`__pycache__` 入库**：**禁止**在本轮或未立项任务中将字节码产物加入提交。
- **修改 `.gitignore`**：**本轮**不得为解决「看得到未跟踪/缓存文件」擅自调整忽略策略抵消风险。
- **与 `execution_service` / `risk_engine` / `shared` 的 pending 草稿**捆在一起处理：**禁止**在未立项下联批决策。
- **与 **`local_box` 扩面**混做一单**：**禁止**。

---

## 6. 后续处理规则

- 若要处理 **`cloud/`**，必须先 **新唯一立项**。
- 立项时必须先选：**归档 / 删除 / 升格为真实长期服务** 之一为主路线（可多阶段，但必须写清）。
- 必须同步说明：**`shared` 依赖边界**如何处理，以及 **`9002`/`local_box` HTTP 假设**是否保留或替换。
- 必须写明 **验收** 与 **回滚**。
- **未立项前**：维持 **`pending_decision`** 口径。

---

## 7. 验收口径（针对「新增本决策记录」这一轮）

- 本轮在父仓库内 **只允许新增**：**`docs/CLOUD_PENDING_DECISION_RECORD_V1.md`**。
- **`git status`** 中 **`cloud/`** 仍应保持 **未跟踪**（不出现因本记录导致的 **`cloud/` 被暂存/删除/移动**）。
- 不出现 **`git add cloud/`**、`__pycache__`** 入库**、或对 **`.gitignore`** 的非授权修改。

---

## 8. 回滚方法

- 删除本文件 **`docs/CLOUD_PENDING_DECISION_RECORD_V1.md`** 即可撤回本条「决策口径」的文字层冻结。
- 回滚 **不影响**：`cloud/` 草稿、`local_box`、`shared`、`execution_service`、`risk_engine`、`anchor-backend`、`anchor-console` 子模块等业务树内容——它们保持原物理状态与其它任务节奏。

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

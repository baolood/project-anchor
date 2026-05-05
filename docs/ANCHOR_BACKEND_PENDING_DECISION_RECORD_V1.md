# ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1

## 1. 结论

- **`anchor-backend/`** subtree：**`git ls-files --others --exclude-standard` 语境下仍为未跟踪的草稿文件为 **1** 个（见 §2.3）；另有 **§2.1／§2.2** 所示路径 **已升格或已归档**（跟踪对象均 **不再**出现于 **`git ls-files --others`**）。
- **当前**：不删除、不移动 §2.3 **仍未跟踪**路径，亦 **不以未立项方式直接并入主线**。
- **§2.3**：统一状态 **`pending_decision`**。
- **建议策略（冻结口径）：** **保留待立项**，**逐项**决定是否归档、删除或升格。
- **`git add anchor-backend/` 「一把梭」：** **严禁**在未单列任务与路径白名单前提下执行。

---

## 2. 当前文件清单

### 2.1 已升格（跟踪）

- **`anchor-backend/docs/DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`**
  - 例：**`fcc76b3`** **`docs: add domain command validation dev usage`**
  - 语义：**dev-only**，**≠** 生产 **`/domain-commands`** 主执行链（见下文 §3）。

### 2.2 已归档（跟踪；父仓 **`docs/archive/…`**）

- **`docs/archive/anchor_backend_draft/worker/WORKER_BOUNDARY_RULES.md`**
  - 由原 **`anchor-backend/worker/WORKER_BOUNDARY_RULES.md`**（未跟踪备忘）迁入；**归档语义**见 **§10**。

### 2.3 仍为未跟踪（ **`pending_decision`** ）

- **`anchor-backend/scripts/insert_order_command.py`**

---

## 3. 用途摘要

### `DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`

- **dev-only** 路由 **`POST /domain-command-validation-dev`** 的 **使用说明**（**`curl`** 示例、正向/反向 **quote** 校验场景）。
- 与返回体中的 **`summary` / `validation`** 稳定键语义相关。
- **不代表** **`/domain-commands` …** 一类 **生产域指令执行主链**；文档自身亦声明不接主执行链。

### `insert_order_command.py`

- 面向 **本地 Postgres** 的 **`commands` 表** **灌数据脚本**：插入 **`type=order`**、状态 **`pending`** 的示例命令行。
- **含硬编码 **`DB_HOST`/`DB_*`/`DB_PASSWORD`** 等连接参数**：在未完成 **密钥/配置治理** 前 **不适合**作为 **正式主线工具**入库。

### `WORKER_BOUNDARY_RULES.md`（归档副本）

- **Worker 改动边界治理备忘**（**Safe / Delivery / Critical** 分档）。
- **不是**可执行代码，亦非 HTTP/API 契约；**正式 runbook 若吸收本条，须立项重指主归宿**。

---

## 4. 与当前主线关系

- **`DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`**（已跟踪）：与 **`commands_domain`** **开发侧验证链有关**，但 **仅限 dev-only**，**≠**生产执行主契约。
- **`insert_order_command.py`**：与 **`commands` 数据面** **弱相关**（写入表），**不是** **`HTTP`/`worker`** 契约层组件。
- **`WORKER_BOUNDARY_RULES.md`**（**§2.2 归档跟踪**）：与 **worker 治理叙事**相关，但 **不是 API 契约**或执行链路定义正文。
- **上述材料**与 **`local_box` baseline**（**`scripts/check_local_box_baseline.sh`** + 已入库最小 **`local_box/`** 路径 + CI）**无直接关系**。

---

## 5. 是否进入正式主线的判断

| 文件 | 判断 |
|------|------|
| **`DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`** | **已升格为受控 docs**（ **`anchor-backend/docs/`** ，例 **`fcc76b3`**）；后续变更仍须绑定 **生产/dev 分区**与维护责任。 |
| **`insert_order_command.py`** | **默认不进入正式主线**；若要入库，须 **先行移除硬编码 DB 机密**、改用 **ENV/密钥管理**，并补齐 **README/验收**。 |
| **`WORKER_BOUNDARY_RULES.md`** | **已归档**至 **`docs/archive/anchor_backend_draft/worker/WORKER_BOUNDARY_RULES.md`**；若升格为正式运维文档，须 **新立项**并 **去重**既有 worker 文档。 |

截至本条记录：**§2.1／§2.2** 均 **已跟踪**；**§2.3 一份**仍为 **`pending_decision`** **未跟踪**。

---

## 6. 当前禁止动作

- **`git add anchor-backend/`**：**禁止**「一把梭」式暂存整个目录。
- **删除或移动**上述 **§2.3 pending** 草稿路径：**禁止**在未授权任务下执行。
- **在未治理改造完成前**：**禁止**将仍含明文 **`DB` / 密码** 形态的 **`insert_order_command.py`** 纳入版本提交。
- **修改 `.gitignore`**：**本轮**不得以忽略规则粉饰未决风险。
- **与 **`cloud` / `execution_service` / `risk_engine` / `shared`** pending 草稿联批：`git add` / 同一 commit **混提**：**禁止**。
- **借此推进 `local_box` 扩面：** **禁止**。

---

## 7. 后续处理规则

- 若处理 **anchor-backend** §2.3 pending 文件：必须先 **新唯一立项**。
- **一轮**：只处理 **一个文件**，或预先写清的 **一个小组合**。
- **立项**：必选 **归档 / 删除 / 升格入库（或升格为受控路径）** 之一为主线（可多阶段，须写明）。
- **涉及脚本升格**：必须先裁决 **数据库参数、密钥、运行环境边界**。
- **必须定义** **验收** 与 **回滚**。
- **未立项前**：§2.3 维持 **`pending_decision`**。

---

## 8. 验收口径（针对「新增本决策记录」这一轮）

- **本轮**：父仓库内 **只允许新增** **`docs/ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1.md`**。
- **`git status`**：§2.3 **pending** 路径仍应保持 **未跟踪**形态。（§2.1／§2.2 已跟踪项应 **不出现** **`??`**。）
- 不出现：**整目录误暂存**、**pending 草稿被删被移**；**不改 `.gitignore`**。
- 不改 `local_box`、`cloud`、`execution_service`、`risk_engine`、`shared` 的源代码或既有策略文件（本条任务边界）。

---

## 9. 回滚方法

- 删除本文件 **`docs/ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1.md`** 即可撤回本条「决策口径」的文字层冻结。
- 回滚 **不影响**：`anchor-backend/` 草稿实体、`local_box`、`cloud`、`execution_service`、`risk_engine`、`shared`、`anchor-console` 子模块等业务树内容。

---

## 10. Worker 边界备忘 · 归档锚点

- **跟踪路径：** **`docs/archive/anchor_backend_draft/worker/WORKER_BOUNDARY_RULES.md`**
- **原未跟踪路径：** **`anchor-backend/worker/WORKER_BOUNDARY_RULES.md`** —— **不应再**以 **`??`** 形态出现在工作区；若有人恢复该路径，视同 **新草稿**，须 **重新立项**。
- **归档语义：** 与 **`cloud` 草稿归档**同类 —— **历史备忘留痕**，**不等于**已并入正式 on-call / SRE runbook。

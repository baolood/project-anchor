# ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1

## 1. 结论

- **`anchor-backend/`** subtree 当前有 **3** 个未跟踪 **pending** 草稿文件（见 §2）。
- **当前**：不删除、不移动这三份路径，亦 **不以未立项方式直接并入主线**。
- **统一状态：** **`pending_decision`**。
- **建议策略（冻结口径）：** **保留待立项**，**逐项**决定是否归档、删除或升格。
- **`git add anchor-backend/` 「一把梭」：** **严禁**在未单列任务与路径白名单前提下执行。

---

## 2. 当前文件清单

- **`anchor-backend/docs/DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`**
- **`anchor-backend/scripts/insert_order_command.py`**
- **`anchor-backend/worker/WORKER_BOUNDARY_RULES.md`**

---

## 3. 用途摘要

### `DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`

- **dev-only** 路由 **`POST /domain-command-validation-dev`** 的 **使用说明**（**`curl`** 示例、正向/反向 **quote** 校验场景）。
- 与返回体中的 **`summary` / `validation`** 稳定键语义相关。
- **不代表** **`/domain-commands` …** 一类 **生产域指令执行主链**；文档自身亦声明不接主执行链。

### `insert_order_command.py`

- 面向 **本地 Postgres** 的 **`commands` 表** **灌数据脚本**：插入 **`type=order`**、状态 **`pending`** 的示例命令行。
- **含硬编码 **`DB_HOST`/`DB_*`/`DB_PASSWORD`** 等连接参数**：在未完成 **密钥/配置治理** 前 **不适合**作为 **正式主线工具**入库。

### `WORKER_BOUNDARY_RULES.md`

- **Worker 改动边界治理备忘**（**Safe / Delivery / Critical** 分档）。
- **不是**可执行代码，亦非 HTTP/API 契约。

---

## 4. 与当前主线关系

- **`DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`**：与 **`commands_domain`** **开发侧验证链有关**，但 **仅限 dev-only**，**≠**生产执行主契约。
- **`insert_order_command.py`**：与 **`commands` 数据面** **弱相关**（写入表），**不是** **`HTTP`/`worker`** 契约层组件。
- **`WORKER_BOUNDARY_RULES.md`**：与 **worker 治理叙事**相关，但 **不是 API 契约**或执行链路定义正文。
- **三者**皆与 **`local_box` baseline**（**`scripts/check_local_box_baseline.sh`** + 已入库最小 **`local_box/`** 路径 + CI）**无直接关系**。

---

## 5. 是否进入正式主线的判断

| 文件 | 判断 |
|------|------|
| **`DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`** | **可在单独任务**评估是否 **升格为受控 docs**（与生产路由分区、索引、维护责任人绑定）。 |
| **`insert_order_command.py`** | **默认不进入正式主线**；若要入库，须 **先行移除硬编码 DB 机密**、改用 **ENV/密钥管理**，并补齐 **README/验收**。 |
| **`WORKER_BOUNDARY_RULES.md`** | **可在 worker 治理任务**中评估是否 **并入正式 runbook/运维文档体系**。 |

截至本条记录，三者均维持 **`pending_decision`**。

---

## 6. 当前禁止动作

- **`git add anchor-backend/`**：**禁止**「一把梭」式暂存整个目录。
- **删除或移动**上述 **pending** 草稿路径：**禁止**在未授权任务下执行。
- **在未治理改造完成前**：**禁止**将仍含明文 **`DB` / 密码** 形态的 **`insert_order_command.py`** 纳入版本提交。
- **修改 `.gitignore`**：**本轮**不得以忽略规则粉饰未决风险。
- **与 **`cloud` / `execution_service` / `risk_engine` / `shared`** pending 草稿联批：`git add` / 同一 commit **混提**：**禁止**。
- **借此推进 `local_box` 扩面：** **禁止**。

---

## 7. 后续处理规则

- 若处理 **anchor-backend** 任一 pending 文件：必须先 **新唯一立项**。
- **一轮**：只处理 **一个文件**，或预先写清的 **一个小组合**。
- **立项**：必选 **归档 / 删除 / 升格入库（或升格为受控路径）** 之一为主线（可多阶段，须写明）。
- **涉及脚本升格**：必须先裁决 **数据库参数、密钥、运行环境边界**。
- **必须定义** **验收** 与 **回滚**。
- **未立项前**：维持 **`pending_decision`**。

---

## 8. 验收口径（针对「新增本决策记录」这一轮）

- **本轮**：父仓库内 **只允许新增** **`docs/ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1.md`**。
- **`git status`**：§2 所列 **pending** 路径仍应保持 **未跟踪**形态。
- 不出现：**整目录误暂存**、**pending 草稿被删被移**；**不改 `.gitignore`**。
- 不改 `local_box`、`cloud`、`execution_service`、`risk_engine`、`shared` 的源代码或既有策略文件（本条任务边界）。

---

## 9. 回滚方法

- 删除本文件 **`docs/ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1.md`** 即可撤回本条「决策口径」的文字层冻结。
- 回滚 **不影响**：`anchor-backend/` 草稿实体、`local_box`、`cloud`、`execution_service`、`risk_engine`、`shared`、`anchor-console` 子模块等业务树内容。

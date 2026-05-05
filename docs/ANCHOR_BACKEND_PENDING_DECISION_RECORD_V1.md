# ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1

## 1. 结论

- **`anchor-backend/`** subtree：就 **本簇曾登记的 pending 草稿**而言，**`git ls-files --others --exclude-standard` 下已无残留**；条目均已 **升格跟踪**（见 §2.1）或 **归档入库**（见 §2.2）。
- **当前**：不因本簇收口而 **顺带**解除 **`execution_service` / `risk_engine` / `shared`** 等 **其它 pending 簇**的立项纪律；亦不借本簇隐含推进 **`local_box` 扩面**。
- **建议策略：** 若未来 **重新**出现 **`anchor-backend/`** 下 **未跟踪**实验文件，视同 **新材料**，仍须 **逐项唯一立项**。
- **`git add anchor-backend/` 「一把梭」：** **严禁**在未单列任务与路径白名单前提下执行。

---

## 2. 当前文件清单

### 2.1 已升格（跟踪；不出现于 `git ls-files --others --exclude-standard`）

- **`anchor-backend/docs/DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`**
  - 例：**`fcc76b3`** **`docs: add domain command validation dev usage`**
  - 语义：**dev-only**，**≠** 生产 **`/domain-commands`** 主执行链（见下文 §3）。

- **`anchor-backend/scripts/insert_order_command.py`**
  - 例：**`9c20d55`** **`fix(scripts): require ANCHOR_DB_* env for sample order insert`**
  - **本地 Postgres **`commands`** 表** 写入示例：**`type=order`** / **`pending`**。
  - **连接参数：** 仅 **`ANCHOR_*`** **环境变量**；**`ANCHOR_DB_PASSWORD` 必填**；**无主线条目常量口令**。运行说明见 **脚本首注释**与 **§11**。

### 2.2 已归档（跟踪；父仓 **`docs/archive/…`**）

- **`docs/archive/anchor_backend_draft/worker/WORKER_BOUNDARY_RULES.md`**
  - 由原 **`anchor-backend/worker/WORKER_BOUNDARY_RULES.md`**（未跟踪备忘）迁入；**归档语义**见 **§10**。

---

## 3. 用途摘要

### `DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`

- **dev-only** 路由 **`POST /domain-command-validation-dev`** 的 **使用说明**（**`curl`** 示例、正向/反向 **quote** 校验场景）。
- 与返回体中的 **`summary` / `validation`** 稳定键语义相关。
- **不代表** **`/domain-commands` …** 一类 **生产域指令执行主链**；文档自身亦声明不接主执行链。

### `insert_order_command.py`

- 面向 **本地 Postgres **`commands`**** 的 **示例灌单行**脚本；便于开发/冒烟时构造 **`pending`** **`order`** 命令形态。
- **不可**在无 **`ANCHOR_DB_PASSWORD`**（及可达库实例）时使用；口令 **只允许经环境传入**。

### `WORKER_BOUNDARY_RULES.md`（归档副本）

- **Worker 改动边界治理备忘**（**Safe / Delivery / Critical** 分档）。
- **不是**可执行代码，亦非 HTTP/API 契约；**正式 runbook 若吸收本条，须立项重指主归宿**。

---

## 4. 与当前主线关系

- **`DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`**：与 **`commands_domain`** **开发侧验证链有关**，但 **仅限 dev-only**，**≠**生产执行主契约。
- **`insert_order_command.py`**：与 **`commands` 数据面** **弱相关**（写入表），**不是** **`HTTP`/`worker`** 契约层组件。
- **`WORKER_BOUNDARY_RULES.md`**（**§2.2**）：与 **worker 治理叙事**相关，但 **不是 API 契约**或执行链路定义正文。
- **上述材料**与 **`local_box` baseline**（**`scripts/check_local_box_baseline.sh`** + 已入库最小 **`local_box/`** 路径 + CI）**无直接关系**。

---

## 5. 是否进入正式主线的判断

| 文件 | 判断 |
|------|------|
| **`DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md`** | **已升格为受控 docs**（ **`anchor-backend/docs/`** ，例 **`fcc76b3`**）；后续变更仍须绑定 **生产/dev 分区**与维护责任。 |
| **`insert_order_command.py`** | **已升格为受控脚本**（**仅限 ENV 密钥**）；若未来增强（CLI 参数、`--dry-run` 等），须 **单列任务**。 |
| **`WORKER_BOUNDARY_RULES.md`** | **已归档**至 **`docs/archive/anchor_backend_draft/worker/WORKER_BOUNDARY_RULES.md`**；若升格为正式运维文档，须 **新立项**并 **去重**既有 worker 文档。 |

截至本条记录：**§2** 所列路径 **均已跟踪**。

---

## 6. 当前禁止动作

- **`git add anchor-backend/`**：**禁止**「一把梭」式暂存整个目录。
- **破坏已跟踪 **`anchor-backend/`** 源码或 docs：** **禁止**在未授权任务下 **删除／挪作他用**。（回滚可走 Git。）
- **禁止**再将 **`insert_order_command.py`** 改回 **`DB_PASSWORD = "..."`** **类硬编码常量**形态入库（凭证 **仅能**经由 **运行时环境**）。
- **修改 `.gitignore`**：**不得**为了解决「看得见未跟踪」而擅自粉饰风险（若确需 **`gitignore`** 变更，必须 **单列立项**）。
- **与 **`cloud` / `execution_service` / `risk_engine` / `shared`** pending 草稿 **联批** `git add` / **同一 commit 混提：** **禁止**。
- **借此推进 `local_box` 扩面：** **禁止**。

---

## 7. 后续处理规则

- 将来若 **`anchor-backend/`** subtree **再次出现** **未跟踪**实验文件：**必须先 ****新唯一立项****。
- **一轮**：只处理 **一个路径**或立项写清的 **极小组合**。
- **立项**：必选 **归档 / 删除 / 升格入库（或升格为受控路径）** 之一为主线（可多阶段，须写明）。
- **脚本类升格**：口令/密钥边界须 **先于** **`git commit`** **写清验收**。
- **必须定义** **验收** 与 **回滚**。

---

## 8. 验收口径（针对「新增本决策记录」第一轮）

- **历史**：父仓库内 **首轮** **只允许新增** **`docs/ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1.md`**。（后续增补须在 **单列任务**中验收。）

---

## 9. 回滚方法

- 删除本文件 **`docs/ANCHOR_BACKEND_PENDING_DECISION_RECORD_V1.md`** 即可撤回本条「决策口径」的文字层冻结。
- 回滚 **不影响**：已入库 **`anchor-backend/`** 源码与 docs、其它子系统等——它们仍由各自的 Git **对象与提交链**保有。

---

## 10. Worker 边界备忘 · 归档锚点

- **跟踪路径：** **`docs/archive/anchor_backend_draft/worker/WORKER_BOUNDARY_RULES.md`**
- **原未跟踪路径：** **`anchor-backend/worker/WORKER_BOUNDARY_RULES.md`** —— **不应再**以 **`??`** 形态出现在工作区；若有人恢复该路径，视同 **新草稿**，须 **重新立项**。
- **归档语义：** 与 **`cloud` 草稿归档**同类 —— **历史备忘留痕**，**不等于**已并入正式 on-call / SRE runbook。

---

## 11. **`insert_order_command.py` · 升格锚点**

- **跟踪路径：** **`anchor-backend/scripts/insert_order_command.py`**
- **必填：** **`ANCHOR_DB_PASSWORD`**。
- **可选（有非密钥默认值）：** **`ANCHOR_DB_HOST`**、**`ANCHOR_DB_PORT`**、**`ANCHOR_DB_NAME`**、**`ANCHOR_DB_USER`** —— **细节以脚本顶端说明为准**。

# SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1

## 1. 结论

- **`shared/schemas.py`**（及 **`shared/__init__.py`**）已 **升格为父仓跟踪对象**（见 **§9**），**不再**出现在 **`git ls-files --others --exclude-standard`**。
- **语义：** **`shared.schemas`** 现为 **仓库内可见的类型契约模块**（**草稿级 dataclass/Enum 集合**），**不等于**已走完 **schema 治理/版本化/破坏性变更门槛** 的 **正式封板契约库**——后续演进须 **单列立项**。
- **`local_box` 已入库 import：** 干净 clone + 检出后 **`from shared.schemas import …`** **可解析**（此前 **未跟踪 **`shared/`** 造成的 import 缺口**已收口于 **「文件已跟踪」**层面；**语义/兼容**仍由业务变更与 CI 约束）。

---

## 2. 当前文件清单（跟踪）

- **`shared/__init__.py`**
- **`shared/schemas.py`**

**说明：** **`shared/__pycache__/`** 为 **本地产物**，**不得**入库。

---

## 3. 用途摘要

**`shared/schemas.py`**：**草稿级共享类型** —— **`StrategyIntent`**、**`NormalizedCommand`**、**`Stage`/`StageResult`**、**`ExecutionTicket`/`ExecutionResult`**、**`ExecMode`/`Status`**、**`Event`** 与若干 **id 生成器**；用于并行实验骨架与 **`local_box`** 等路径的 **结构对齐**。

---

## 4. 依赖关系（消费方快照）

- **`docs/archive/cloud_draft/…`**、**`docs/archive/execution_service_draft/…`**、**`docs/archive/manual_smoke/test_*.py`**、**`local_box/`**、**`risk_engine/`**（跟踪 **`client.py`**）等：**可能** **`from shared.schemas import …`**（以各路径 **实现与 PYTHONPATH** 为准）。
- **归档段**对 **`shared`** 的依赖 **不宣称**「归档树在本仓库默认布局下可一键跑通」。

---

## 5. 与当前主线关系

- 与 **`commands_domain`** **无直接关系**。
- 与 **`local_box` baseline** CI：**baseline 仍不必然**验证 **全部 **`shared`** 类型组合**；**不得**用「CI 绿」**单独**证明 **schema 已封板**。

---

## 6. 当前禁止动作

- **`git add shared/`** **一把梭**（在未写清白名单的立项下）：**禁止**。
- **`__pycache__` 入库**：**禁止**。
- **把 **`shared.schemas`** 当「不可改圣经」却又不写兼容策略：** **禁止**（须立项定义 **版本/弃用/迁移**）。
- **与 **`risk_engine`/`execution_service`/`cloud`** 的 **未授权** 契约漂移 **混提交、无说明：** **禁止**。

---

## 7. 后续处理规则

- **破坏性变更**、**拆包/搬迁**、**生成 schema 源**等：**须单列立项** + **验收** + **回滚**。
- **与 **`local_box`** 扩面/重构** 强耦合的 **`shared`** 改动：**须**在任务中 **显式**列出 **import 面与迁移步骤**。

---

## 8. 验收口径（历史首轮）

- 首轮 **只允许新增** **`docs/SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1.md`**。

---

## 9. 回滚方法

- 删除 **`docs/SHARED_SCHEMAS_PENDING_DECISION_RECORD_V1.md`** 仅撤回 **文字口径**层；**不自动**撤销 **`shared/`** 已跟踪文件（须另走 Git 回滚）。

---

## 10. 升格锚点（`shared/`）

- **例提交：** **`6ee8365`** **`feat(shared): track schemas package; archive risk_engine draft client`**
- **跟踪路径：** **`shared/__init__.py`**、**`shared/schemas.py`**
- **升级口径：** **跟踪入库 ≠** 已完成 **企业级 schema 治理**；**正式契约库**叙事须 **另行立项**。

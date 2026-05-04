# PARENT_WORKTREE_PENDING_LAYER_MAP_V1

## 1. 目标

- 本文档只收口父仓库当前仍未进入主线的工作区内容分层
- 只描述事实，不做实现，不做合并，不做删除

## 2. 当前已知范围

### 2.0 domain_command_worker · strategy guard（已封板 · 事实记录）

- **代码**：`anchor-backend/app/workers/domain_command_worker.py` 内 strategy guard 已按 5 刀落地（top-level forbidden、nested bypass 常量与深度、nested 扫描、`_risk_guard` 接入 top-level 与 nested 检查）。
- **端到端**：已通过最小 HTTP 验收（`POST /domain-commands/quote`、扁平 quote payload）；证据与样例结论见 `docs/DOMAIN_COMMAND_WORKER_STRATEGY_GUARD_E2E_RESULT_V1.md`（top-level / nested / 正常不命中三类）。
- **封板文档**：`docs/DOMAIN_COMMAND_WORKER_STRATEGY_GUARD_CLOSEOUT_V1.md`。
- **边界**：当前明确 **不进入第六刀**，不在此线上追加实现。
- **后续**：若再动 worker guard，须先定义 **新的唯一验收目标** 并单独任务文档；不得沿用本条已封板主线继续扩刀。

### 2.1 `local_box` · baseline 已入库（事实）

- **`local_box/` 下 10 个 `.py` 已纳入 `main`**（始于 `ddd718c` 一类提交），以满足 **`scripts/check_local_box_baseline.sh`** 的最小存在性检查；CI：**`.github/workflows/local-box-baseline.yml`**。
- **状态总览 / 运行留痕：** `docs/LOCAL_BOX_BASELINE_SCRIPT_STATUS_V1.md`、`docs/LOCAL_BOX_BASELINE_WORKFLOW_RUN_EVIDENCE_V1.md`。
- **边界：** 上述事实 **仅**说明「baseline 对象在树里 + 可自动验」；**不**等同于 `local_box` 全套业务已在主线验收完成。

### 2.2 backend 已跟踪未提交修改

- `anchor-backend/app/risk/policy_engine.py`
- `anchor-backend/app/workers/domain_command_worker.py`

### 2.3 父仓库未跟踪实验目录 / 骨架

- `cloud/`
- `execution_service/`
- `risk_engine/`
- `shared/`

（目录树抽样由 `find <上列目录> -maxdepth 2` 生成；证据文件见下文「5. 本轮证据路径」。）

### 2.4 父仓库其它未跟踪（非上列四目录）

- `anchor-backend/docs/`
- `anchor-backend/scripts/insert_order_command.py`
- `anchor-backend/worker/WORKER_BOUNDARY_RULES.md`
- `anchor.db`（父仓库 `.gitignore` 已忽略，本地生成物不入库）
- `test_ack_semantics.py`
- `test_cloud_publish.py`
- `test_execution_service.py`

### 2.5 处理原则

- 上述内容当前一律不算主线完成度
- 在未单独立任务、单独验收、单独提交前，不允许混入主线提交
- 下一轮若推进，只允许从中选一个唯一目标，单独处理

## 3. 当前唯一判断

- `domain_command_worker` 的 strategy guard 主线已从「进行中」收口为 **已封板**（见 §2.0），不再默认视为待推进主线。
- 父仓库仍存在 backend 草稿与 **部分**实验目录草稿（`local_box` baseline 所需路径除外，见 §2.1）
- 这些内容必须先作为“待分层候选”管理
- 现阶段不得并行推进多个方向

## 4. 本轮不做什么

- 不修改 backend 代码
- 不恢复或删除实验目录
- 不提交 `cloud/`、`execution_service/`、`risk_engine/`、`shared/`（**未经单独任务授权时**；`local_box` 已入库部分见 §2.1，勿重复当作「全盘未入库」）
- 不更新子模块

## 5. 本轮证据路径（本地生成，不入库）

- `/tmp/project_anchor_status_short.txt` — 父仓库 `git status --short` 全文
- `/tmp/project_anchor_status_backend.txt` — `git status --short anchor-backend`
- `/tmp/project_anchor_experiment_dirs.txt` — `find cloud execution_service risk_engine shared -maxdepth 2` 输出（`local_box` 已跟踪路径以 `git ls-files local_box` 为准，见 §2.1）

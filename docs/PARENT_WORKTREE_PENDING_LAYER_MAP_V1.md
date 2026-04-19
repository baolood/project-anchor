# PARENT_WORKTREE_PENDING_LAYER_MAP_V1

## 1. 目标

- 本文档只收口父仓库当前仍未进入主线的工作区内容分层
- 只描述事实，不做实现，不做合并，不做删除

## 2. 当前已知范围

### 2.1 backend 已跟踪未提交修改

- `anchor-backend/app/risk/policy_engine.py`
- `anchor-backend/app/workers/domain_command_worker.py`

### 2.2 父仓库未跟踪实验目录 / 骨架

- `cloud/`
- `execution_service/`
- `local_box/`
- `risk_engine/`
- `shared/`

（目录树抽样由 `find <上列目录> -maxdepth 2` 生成；证据文件见下文「5. 本轮证据路径」。）

### 2.3 父仓库其它未跟踪（非上列五目录）

- `anchor-backend/docs/`
- `anchor-backend/scripts/insert_order_command.py`
- `anchor-backend/worker/WORKER_BOUNDARY_RULES.md`
- `anchor.db`
- `test_ack_semantics.py`
- `test_cloud_publish.py`
- `test_execution_service.py`

### 2.4 处理原则

- 上述内容当前一律不算主线完成度
- 在未单独立任务、单独验收、单独提交前，不允许混入主线提交
- 下一轮若推进，只允许从中选一个唯一目标，单独处理

## 3. 当前唯一判断

- 父仓库仍存在 backend 草稿与实验目录草稿
- 这些内容必须先作为“待分层候选”管理
- 现阶段不得并行推进多个方向

## 4. 本轮不做什么

- 不修改 backend 代码
- 不恢复或删除实验目录
- 不提交 `cloud/`、`execution_service/`、`local_box/`、`risk_engine/`、`shared/`
- 不更新子模块

## 5. 本轮证据路径（本地生成，不入库）

- `/tmp/project_anchor_status_short.txt` — 父仓库 `git status --short` 全文
- `/tmp/project_anchor_status_backend.txt` — `git status --short anchor-backend`
- `/tmp/project_anchor_experiment_dirs.txt` — `find cloud execution_service local_box risk_engine shared -maxdepth 2` 输出

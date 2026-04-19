# DOMAIN_COMMAND_WORKER_WIP_RECOVERY_SOURCE_CHECK_V1

## 1. 目标

- 本文档只回答一个问题：
- `domain_command_worker.py` 被覆盖前的旧 WIP 是否仍有可恢复来源

## 2. 当前事实

- 第一刀已正式落库（提交 `b43a9c0`）
- 当前磁盘文件为：**已发布历史 + 第一刀插入**，**不是**此前工作区中约 **~1483 行插入** 那一整包未提交 WIP
- 在未确认恢复来源前，不允许直接进入第二刀

## 3. 核查范围

- `git stash list`（父仓库 `project-anchor`）
- `stash@{0}` … `stash@{4}` 的 `--stat` 是否含 `anchor-backend/app/workers/domain_command_worker.py`
- 各 stash 中与 worker 相关的 patch 体量（从完整 `git stash show -p` 中截取 `domain_command_worker.py` 片段；`git stash show -p stash@{n} -- <path>` 在本环境 Git 下报错，故采用截取法）
- `git log --all --oneline -- anchor-backend/app/workers/domain_command_worker.py` 前若干条

## 4. 唯一结论

- **有恢复来源 / 无恢复来源 / 仍不确定**：**无恢复来源**（针对「**与 checkout 前工作区一致的那包约 1500 行级 WIP**」这一对象）。
- **具体说明**：
  - 父仓库 **`stash@{0}`**、**`stash@{2}`** 的 stat **不含** `domain_command_worker.py`；导出片段为空（见 `/tmp/worker_stash0.diff`，0 行）。
  - **`stash@{1}`**、**`stash@{3}`**、**`stash@{4}`** 虽在 stat 中出现该文件，但截取到的 patch 分别约 **99 / 68 / 21 行**，内容为 **`domain_worker_loop` 内局部逻辑（如 rate limit guard 等）** 等**旧上下文小改**，与已丢失的 **大块策略校验链插入** **不是同一草稿**。
  - **`git log --all`** 中不存在「含该 ~1483 行插入、且未在 `main` 上」的提交；最近历史为 **`b43a9c0`**（第一刀）、**`73b9bb4`**（read-only fetch 归一）等已发布提交。
  - **子模块 `anchor-console`** 历史中的 `wip-before-ops-060-cleanup` 等 stash **属于前端仓库**，**不包含** 本路径下的 `anchor-backend/app/workers/domain_command_worker.py`。

## 5. 下一步规则

- 结论为 **无恢复来源**（就 mega WIP 而言）：**明确承认**该包旧 WIP **不再作为可依赖资产**；**下一轮第二刀只能基于当前 `main`（含已落库第一刀）重新规划与切片**，不得假设「还能从某 stash 整包捡回」。
- 若日后发现 **新的** 恢复介质（例如另一台机器、未同步的备份、fork 上的分支），应 **新开唯一任务** 再谈合并，不得与本核查结论混用。

## 6. 本轮不做什么

- 不恢复文件到工作区
- 不修改 `domain_command_worker.py`
- 不提交 backend 代码

## 7. 只读证据路径（本地 /tmp，不入库）

- `/tmp/worker_stash0.diff` — **0 行**（`stash@{0}` 无 worker 变更）
- `/tmp/worker_stash1.diff` — 从 `stash@{1}` 截取的 worker 片段（约 99 行）
- `/tmp/worker_stash3.diff`、**/tmp/worker_stash4.diff** — 同上（约 68 / 21 行）
- `/tmp/stash1_full.patch` — `stash@{1}` 全量 patch（约 977 行），可交叉核对

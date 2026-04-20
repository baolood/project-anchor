# LOCAL_BOX_BASELINE_WORKFLOW_RUN_EVIDENCE_V1

> **留痕说明**：下列 §1–§6 来自 **GitHub** 上已 **完成** 的一次 `local-box-baseline` workflow 运行（含公开 API 可复核字段）；**不得**用本地手跑替代远程 run 作为冻结证据。首次冻结：**run `24642983527`**（`2026-04-20`）。

## 1. 本次运行对应的分支名

- **`feature/local-box-baseline-script-v1`**

## 2. 本次运行触发方式

- **`push`**

## 3. GitHub Actions workflow 名称

- **`local-box-baseline`**

## 4. 关键步骤名称

- **`Run local box baseline check`**

## 5. 本次实际结果

- **`failure`**（与 GitHub Actions 对该 workflow run 的 `conclusion` 一致）

## 6. 日志关键证据（摘引）

- **Workflow run（可点开核对）：** [`24642983527`](https://github.com/baolood/project-anchor/actions/runs/24642983527) — `display_title`: `ci: add local-box-baseline workflow`；`head_sha`: `8792a9f7e707c43d472178f2c3b7677b8f0dc6d7`。
- **API 复核（无需登录）：** `GET /repos/baolood/project-anchor/actions/runs/24642983527` → `conclusion`: `failure`，`event`: `push`，`head_branch`: `feature/local-box-baseline-script-v1`。
- **步骤级复核：** job id `72050204347` — 步骤 **`Run local box baseline check`** 结论 **`failure`**（`GET .../actions/jobs/72050204347`）。完整 stderr/stdout 正文请在上述 run 页展开该步骤查看（匿名请求无法下载 logs zip）。
- **根因说明（与脚本语义一致，非日志正文摘抄）：** 当前仓库 **`local_box/` 目录未纳入 git 跟踪**，CI 检出后不存在脚本要求的对象，故脚本按设计输出 **FAIL + STOP** 类结果并使 job 失败。

## 7. 本次结论（口径固定）

- 上述结果 **仅证明** baseline check 脚本在该次 workflow 运行中 **按当时仓库状态** 判定为通过或失败。
- **不代表** 整个 **`local_box` 主链**或其它模块已全部验收完成。

## 8. 回滚方法

- 删除 **`docs/LOCAL_BOX_BASELINE_WORKFLOW_RUN_EVIDENCE_V1.md`** 即可；不影响 workflow 与脚本。

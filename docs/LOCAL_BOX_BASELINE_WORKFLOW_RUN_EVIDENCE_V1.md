# LOCAL_BOX_BASELINE_WORKFLOW_RUN_EVIDENCE_V1

> **留痕说明**：§1–§6 冻结 **首次** run（失败，见下文）；§9 冻结**成功** run（含 `local_box` 入树后及后续文档推送）。**不得**用本地手跑替代远程 run。**失败 run：** **`24642983527`**；**成功 run（入树）：** **`24643041767`**；**成功 run（证据文档）：** **`24643098559`**；**成功 run（`main` merge 后）：** **`24643589825`**；**成功 run（`main` 文档推送 `9c6805a`，Run #7）：** **`24643718594`**；**成功 run（`main` 追加 §9.3 / `2f7be15`，Run #13）：** **`24644103202`**；**成功 run（`main` 同步 STATUS+§9.4 / `7758b1f`，Run #14）：** **`24644350931`**（`2026-04-20`）。

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

## 9. 复检运行证据（`local_box` 已跟踪后）

以下为 **第二次** push 触发的同一 workflow；**HEAD** **`ddd718c`**（`chore: track local_box snapshot for baseline check`）。

| 字段 | 值 |
|------|-----|
| 分支 | **`feature/local-box-baseline-script-v1`** |
| 触发 | **`push`** |
| Workflow run | **[`24643041767`](https://github.com/baolood/project-anchor/actions/runs/24643041767)** |
| **`conclusion`**（API） | **`success`** |
| Job id | **`72050363889`** |
| 步骤 **`Run local box baseline check`** | **`success`** |

**API：** `GET /repos/baolood/project-anchor/actions/runs/24643041767`、`GET .../actions/runs/24643041767/jobs`。控制台完整日志见 run 页面展开步骤。

**脚本语义：** 检出含 `local_box/` 所需路径后，baseline 脚本 **PASS**（stdout 含 `PASS`，退出码 `0`）。

### 9.1 成功 run 补记（`04a9847`，与网页 Run #4 一致）

- **Workflow run：** [`24643098559`](https://github.com/baolood/project-anchor/actions/runs/24643098559) — `head_sha` **`04a9847`**（`docs: extend local box workflow run evidence with passing re-run`）— `conclusion`：**`success`**。
- **步骤「Run local box baseline check」stdout 摘引（可逐字对照 Actions 控制台）：**
  - `Run ./scripts/check_local_box_baseline.sh`
  - `LOCAL_BOX_BASELINE_CHECK PASS: required local_box baseline objects present`

### 9.2 合并至 `main` 后的运行（网页 Run #6）

- **分支：** **`main`**（截图：*Triggered via push … to the `main` branch*）。
- **提交：** **`779c2d4`**（`docs: add PASS log line to local box workflow run evidence`）。
- **Workflow run：** **[`24643589825`](https://github.com/baolood/project-anchor/actions/runs/24643589825)** — GitHub UI **run_number**：**`6`** — `conclusion`：**`success`**。
- **并列参考（同一 SHA 在 feature 上再跑一次）：** run **`24643586063`**，`head_branch`：`feature/local-box-baseline-script-v1`，**run_number**：**`5`**，`conclusion`：**`success`**。
- **stdout** 与同脚本 PASS 语义一致（见 §9.1 两行摘引）。

### 9.3 `main` 上文档推送后的运行（网页 Run #7）

- **分支：** **`main`**。
- **提交：** **`9c6805a`**（`docs: record local-box-baseline run on main after merge`）。
- **Workflow run：** **[`24643718594`](https://github.com/baolood/project-anchor/actions/runs/24643718594)** — GitHub UI **run_number**：**`7`** — `conclusion`：**`success`**（与 `GET /repos/baolood/project-anchor/actions/runs/24643718594` 一致）。
- **stdout** 与同脚本 PASS 语义一致（见 §9.1 两行摘引）。

### 9.4 `main` 上 RUN_EVIDENCE 更新后的运行（网页 Run #13）

- **分支：** **`main`**。
- **提交：** **`2f7be15`**（`docs: add main Run #7 to local box workflow run evidence`）。
- **Workflow run：** **[`24644103202`](https://github.com/baolood/project-anchor/actions/runs/24644103202)** — GitHub UI **run_number**：**`13`** — `conclusion`：**`success`**（与 `GET /repos/baolood/project-anchor/actions/runs/24644103202` 一致）。
- **stdout** 与同脚本 PASS 语义一致（见 §9.1 两行摘引）。

### 9.5 `main` 上 RUN_EVIDENCE §9.4 与 STATUS 同步后的运行（网页 Run #14）

- **分支：** **`main`**。
- **提交：** **`7758b1f`**（`docs: record Run #13 in RUN_EVIDENCE and sync baseline STATUS`）。
- **Workflow run：** **[`24644350931`](https://github.com/baolood/project-anchor/actions/runs/24644350931)** — GitHub UI **run_number**：**`14`** — `conclusion`：**`success`**（与 `GET /repos/baolood/project-anchor/actions/runs/24644350931` 一致）。
- **stdout** 与同脚本 PASS 语义一致（见 §9.1 两行摘引）。

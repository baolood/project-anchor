# LOCAL_BOX_BASELINE_SCRIPT_STATUS_V1

## 1. 脚本位置（父仓库）

- **`project-anchor/scripts/check_local_box_baseline.sh`**

## 2. 执行入口

- 在仓库根目录：**`./scripts/check_local_box_baseline.sh`**

## 3. CI 接入（当前事实）

- Workflow：**`.github/workflows/local-box-baseline.yml`**（workflow 名：`local-box-baseline`）。
- **`main`** 已与 feature 工作合流；推送 / PR 会触发该 workflow。
- 详见运行与日志留痕：**`docs/LOCAL_BOX_BASELINE_WORKFLOW_RUN_EVIDENCE_V1.md`**（含首次失败、`local_box` 入库后成功、merge 至 **`main`** 后的运行）。
- **已回填 API 的运行（节选）：** **`9c6805a`** → Run **#7** / [`24643718594`](https://github.com/baolood/project-anchor/actions/runs/24643718594)；**`2f7be15`** → Run **#13** / [`24644103202`](https://github.com/baolood/project-anchor/actions/runs/24644103202)；**`7758b1f`** → Run **#14** / [`24644350931`](https://github.com/baolood/project-anchor/actions/runs/24644350931)；**`abe5fe9`** → Run **#15** / [`25312184296`](https://github.com/baolood/project-anchor/actions/runs/25312184296)；**`9a27a36`** → Run **#16** / [`25315241628`](https://github.com/baolood/project-anchor/actions/runs/25315241628)（见 RUN_EVIDENCE §9.3–§9.7、§9.8 维护口径）。其后 **`main`** 日常推送会再产生 run，**以 Actions 列表或 API 为准即可**，不必每笔都写回本文档。

## 4. 验收语义（脚本）

- **PASS：** stdout 含 `PASS`，退出码 `0`。
- **FAIL：** stderr 含 `FAIL` 与 `STOP`，退出码非 `0`。

## 5. 口径（勿误判）

- **Job 绿**仅表示本次 **baseline 检查**通过，**不代表** entire `local_box` 或其它模块已全部业务验收。

## 6. 回滚

- 卸下自动化：删除或停用 **`.github/workflows/local-box-baseline.yml`**（按仓库流程提交）。
- 卸下脚本：**`scripts/check_local_box_baseline.sh`**（同上）。
- 文档：删除或还原本文件及相关 `LOCAL_BOX_*` 文档不会影响运行时行为，仅影响事实口径。

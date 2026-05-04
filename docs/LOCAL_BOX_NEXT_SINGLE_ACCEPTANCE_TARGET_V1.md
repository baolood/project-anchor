# LOCAL_BOX_NEXT_SINGLE_ACCEPTANCE_TARGET_V1

## 1. 结论

- **`local_box` baseline check** 已从「唯一的下一验收目标」收口为 **已闭环**（脚本、规范、最小 `local_box/` 入库、GitHub Actions、运行留痕均已在 `main`）。
- **`local_box` 的下一步扩面（业务实现、与其它目录联动）仍然没有默认目标**：必须先 **重新立项**，并只允许 **1** 个新的唯一验收文档 / 里程碑，再扩大修改面。

## 2. 已闭环事实（可查）

- **脚本：** `scripts/check_local_box_baseline.sh` — **规范：** `docs/LOCAL_BOX_BASELINE_CHECK_SCRIPT_SPEC_V1.md`
- **CI：** `.github/workflows/local-box-baseline.yml` — **状态 / 语义：** `docs/LOCAL_BOX_BASELINE_SCRIPT_STATUS_V1.md`
- **运行留痕：** `docs/LOCAL_BOX_BASELINE_WORKFLOW_RUN_EVIDENCE_V1.md`（含 §9.8：**不必**对每笔纯文书推送追加 §9.x）
- **baseline 入库与父仓库分层：** `docs/PARENT_WORKTREE_PENDING_LAYER_MAP_V1.md` §2.1
- **立项期验收语义（存档）：** `docs/LOCAL_BOX_BASELINE_CHECK_ACCEPTANCE_V1.md`

## 3. 前置边界（仍为真）

- `docs/LOCAL_BOX_BOUNDARY_AND_ACCEPTANCE_V1.md` 的总体边界仍然适用：**不并行开第二目标**；未获单独授权的实验目录不按主线默认提交。
- 「baseline 所需最小 `local_box/` 路径已入库」**不改变**：未经新任务，仍不把 `local_box/` 当作可随意扩展的实现主线。

## 4. 唯一下一验收目标（当前）

- **未指派。** 须由任务 owner 明示 **下一个且仅一个** 验收目标（新文档或已存在的单一里程碑编号），批准后再进入对应实现或文档扩写。
- **禁止**在未重新定义「唯一下一目标」的情况下，并行修改多个实验目录或把 `local_box/` 扩写成无边界主线。

## 5. 历史：`LOCAL_BOX_BASELINE_CHECK_ACCEPTANCE_V1.md` 轮（已达成）

- 该轮只允许新增验收文档的目标 **已完成**；baseline check 随后在 SPEC / 脚本 / CI 中兑现。追溯语义仍以该文件正文为准。

## 6. 当前明确不做什么

- 不因「baseline 已绿」而默认开始 `local_box/` 全量实现或其它目录联调。
- 不恢复「多目标并行推进」。
- 不把 `LOCAL_BOX_BASELINE_CHECK_ACCEPTANCE_V1.md` 的旧 §3「只允许新增本文档」误解为**当前**仍禁止一切实现（实现已按后续任务发生；见 §2）。

## 7. 一句话判断

- **baseline 已冻结**；**下一步**只能来自 **新立的一项** 验收目标，而不是继续消费本条历史主线。

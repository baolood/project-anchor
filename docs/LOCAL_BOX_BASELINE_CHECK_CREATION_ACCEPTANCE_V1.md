# LOCAL_BOX_BASELINE_CHECK_CREATION_ACCEPTANCE_V1

## 1. 结论

- `scripts/check_local_box_baseline.sh` 当前是否创建，只允许先定义单一验收门槛。
- 在本文件获批并落库前，不创建该脚本，不进入 `local_box` 实现。

## 2. 前置事实

- `docs/LOCAL_BOX_BASELINE_CHECK_EXISTENCE_RESULT_V1.md` 已确认脚本不存在。
- `docs/LOCAL_BOX_BASELINE_CHECK_MISSING_SCRIPT_DISPOSITION_V1.md` 已写死：当前不准直接补脚本。
- 当前阶段只允许先回答：在什么条件下才值得创建该脚本。

## 3. 允许修改范围

- 本轮只允许：
  - 新增 `docs/LOCAL_BOX_BASELINE_CHECK_CREATION_ACCEPTANCE_V1.md`
- 本轮不允许：
  - 创建 `scripts/check_local_box_baseline.sh`
  - 修改 `local_box/`
  - 修改 `execution_service/`
  - 修改 `risk_engine/`
  - 修改 `shared/`
  - 修改 `cloud/`
  - 修改 `anchor-backend/`
  - 修改子模块
  - 并行新增第二个 active 目标

## 4. 创建脚本的唯一验收门槛

- 只有同时满足以下条件，才允许进入“创建脚本”下一步：

1. **职责单一**
   - 脚本只负责 baseline check
   - 不顺手承担部署、修复、启动、迁移等其它职责

2. **入口明确**
   - 从仓库根目录可直接执行
   - 不依赖并行修改多个目录才能成立

3. **结果可判**
   - 输出必须能直接区分 PASS / FAIL
   - 不依赖人工主观解释

4. **失败可停**
   - 一旦 baseline check 失败，后续不允许继续推进 `local_box` 实现

## 5. PASS 条件

- 已写清脚本若被创建时的最小职责
- 已写清脚本的执行入口
- 已写清脚本输出如何直接判断 PASS / FAIL
- 已写清失败后必须停止推进

## 6. FAIL 条件

- 脚本职责不单一
- 入口不明确
- 输出无法直接判断 PASS / FAIL
- 失败后仍不能阻止后续推进
- 仍需并行改多个目录才能成立

## 7. 回滚方法

- 若本轮仅新增本文档：
  - 删除 `docs/LOCAL_BOX_BASELINE_CHECK_CREATION_ACCEPTANCE_V1.md`
- 不涉及代码回滚

## 8. 当前明确不做什么

- 不创建 `scripts/check_local_box_baseline.sh`
- 不执行任何 baseline check
- 不修改 `local_box/`
- 不联动其它目录
- 不把“定义创建门槛”偷换成“开始创建实现”

## 9. 一句话判断

- 现在唯一正确下一步，不是补脚本，而是先把“什么条件下才允许创建该脚本”写死。

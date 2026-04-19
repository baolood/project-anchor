# LOCAL_BOX_BASELINE_CHECK_SCRIPT_SPEC_V1

## 1. 结论

- `scripts/check_local_box_baseline.sh` 若后续允许创建，其当前阶段只允许先定义最小脚本规格。
- 在本文件获批并落库前，不创建该脚本，不执行该脚本。

## 2. 前置事实

- `docs/LOCAL_BOX_BASELINE_CHECK_EXISTENCE_RESULT_V1.md` 已确认脚本不存在。
- `docs/LOCAL_BOX_BASELINE_CHECK_MISSING_SCRIPT_DISPOSITION_V1.md` 已确认当前不准直接补脚本。
- `docs/LOCAL_BOX_BASELINE_CHECK_CREATION_ACCEPTANCE_V1.md` 已写清创建门槛。
- `docs/LOCAL_BOX_BASELINE_CHECK_CREATION_DECISION_V1.md` 已写死：当前暂不允许创建，下一步先写脚本规格。

## 3. 脚本最小职责

- 该脚本若被创建，只允许承担以下最小职责：
  1. 检查 `local_box baseline` 所需对象是否存在
  2. 输出明确的 PASS / FAIL 结果
  3. 在 FAIL 时给出“停止推进”的明确信号

- 该脚本明确不负责：
  - 自动修复
  - 自动创建缺失对象
  - 自动启动服务
  - 修改配置
  - 联动其它目录执行复杂流程

## 4. 标准入口

- 脚本路径固定为：
  - `scripts/check_local_box_baseline.sh`
- 标准执行入口固定为：
  - 从仓库根目录执行该脚本
- 当前阶段只定义入口，不实际执行

## 5. PASS 输出口径

- 该脚本若后续被创建，其 PASS 输出必须满足：
  - 直接可读
  - 明确包含 PASS 语义
  - 不依赖人工解释
- 最小要求：
  - 以脚本退出码与明确文本共同判定 PASS

## 6. FAIL 输出口径

- 该脚本若后续被创建，其 FAIL 输出必须满足：
  - 直接可读
  - 明确包含 FAIL / BLOCK / STOP 语义之一
  - 能支持“当前不得继续推进 local_box 实现”的判断
- 最小要求：
  - 以非 0 退出码与明确文本共同判定 FAIL

## 7. 当前明确不做什么

- 不创建 `scripts/check_local_box_baseline.sh`
- 不执行该脚本
- 不修改 `local_box/`
- 不联动 `execution_service/`、`risk_engine/`、`shared/`、`cloud/`、`anchor-backend/`
- 不把“规格定义”偷换成“开始实现”

## 8. 回滚方法

- 若本轮仅新增本文档：
  - 删除 `docs/LOCAL_BOX_BASELINE_CHECK_SCRIPT_SPEC_V1.md`

## 9. 一句话判断

- 现在唯一正确下一步，不是补脚本，而是先把该脚本的最小职责、入口、PASS/FAIL 输出口径写死。

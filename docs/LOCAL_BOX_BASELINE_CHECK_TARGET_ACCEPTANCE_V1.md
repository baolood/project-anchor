# LOCAL_BOX_BASELINE_CHECK_TARGET_ACCEPTANCE_V1

## 1. 结论

- `scripts/check_local_box_baseline.sh` 当前只允许先定义验收口径。
- 在本文件获批并落库前，不执行该脚本，不修改该脚本。

## 2. 唯一验收对象

- `scripts/check_local_box_baseline.sh`

## 3. 存在性检查方法

- 只允许使用只读方式确认：
  - 文件路径是否存在
  - 是否具备可执行入口语义
- 当前阶段不允许因为“文件不存在/不完整”而顺手补实现

## 4. 执行方式定义

- 当前只定义未来执行时的标准方式：
  - 从仓库根目录进入后执行
  - 以单脚本方式运行
- 本轮不实际执行
- 本轮不补参数、不改调用方式

## 5. PASS 条件

- 能明确回答以下 3 件事：
  1. 文件是否存在
  2. 后续标准执行方式是什么
  3. 运行结果如何直接判断 PASS / FAIL

## 6. FAIL 条件

- 找不到脚本路径
- 无法说明标准执行方式
- 无法说明输出如何区分 PASS / FAIL
- 仍需并行修改多个目录才能定义验收口径

## 7. 回滚方法

- 若本轮仅新增本文档：
  - 删除 `docs/LOCAL_BOX_BASELINE_CHECK_TARGET_ACCEPTANCE_V1.md`
- 不涉及代码回滚

## 8. 当前明确不做什么

- 不执行 `scripts/check_local_box_baseline.sh`
- 不修改 `scripts/check_local_box_baseline.sh`
- 不修改 `local_box/`
- 不联动 `execution_service/`、`risk_engine/`、`shared/`、`cloud/`、`anchor-backend/`
- 不进入 baseline check 实现修复

## 9. 一句话判断

- `local_box baseline check` 的下一步仍不是实现，而是先把脚本对象的验收口径写死：存在、怎么跑、如何判 PASS/FAIL。

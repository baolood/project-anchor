# BACKEND_NEXT_SINGLE_TARGET_V1

## 1. 目标

- 本文档只回答一个问题：
- 父仓库当前剩余 backend 草稿里，下一步唯一应推进哪个文件

## 2. 候选范围

- `anchor-backend/app/risk/policy_engine.py`
- `anchor-backend/app/workers/domain_command_worker.py`

## 3. 排除范围

- `cloud/`
- `execution_service/`
- `local_box/`
- `risk_engine/`
- `shared/`
- `anchor-backend/docs/`
- `anchor-backend/scripts/insert_order_command.py`
- `anchor-backend/worker/WORKER_BOUNDARY_RULES.md`
- `anchor.db`
- 根目录 `test_*.py`

## 4. 判定原则

- 只认当前主线价值
- 只认最小改动
- 只认可验证、可回滚
- 不允许并行推进两个 backend 文件

## 5. 唯一结论

- **`anchor-backend/app/risk/policy_engine.py`**
- **原因简述**：（1）当前工作区相对已跟踪版本的 diff 规模极小（约十余行量级），属于可一眼看完、可单测收口的风险面；（2）变更语义是去掉 `evaluate_single_trade` 路径上误缩进/无效的 `lims = {}`，与「风险单笔 notional 上限」主线直接相关，回滚成本极低。（3）**`domain_command_worker.py`** 的 diff 体量极大（千余行量级），内含标准化策略请求、禁止字段、签名与嵌套扫描等一整条域命令校验链，适合作为**紧随其后的独立大任务**，若与 policy 并行会再次违反「单点推进」纪律，故**本轮不动** `domain_command_worker.py`。

## 6. 本轮不做什么

- 不改 backend 代码
- 不提交 backend 改动
- 不恢复实验目录
- 不更新子模块

## 7. 证据（本地生成，不入库）

- `/tmp/policy_engine.diff` — `git diff -- anchor-backend/app/risk/policy_engine.py`
- `/tmp/domain_command_worker.diff` — `git diff -- anchor-backend/app/workers/domain_command_worker.py`

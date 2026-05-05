# WORKER_BOUNDARY_RULES.md

> **归档说明：** 由原 **`anchor-backend/worker/WORKER_BOUNDARY_RULES.md`**（未跟踪备忘）归档至此；内容为 **worker 改动边界草稿**，不构成生产契约。若升格为正式 runbook，须在立项中写明主归宿。

## Safe（允许）
- 读取任务队列（Redis）
- 执行交易逻辑（受风控限制）
- 写执行结果日志

## Delivery（需谨慎）
- 修改执行流程
- 增加新任务类型
- 调整队列结构

## Critical（禁止自动改）
- 交易执行核心（下单逻辑）
- 风控校验逻辑
- API Key / 账户权限处理

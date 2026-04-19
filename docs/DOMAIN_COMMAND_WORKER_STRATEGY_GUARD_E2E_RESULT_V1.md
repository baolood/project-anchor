# DOMAIN_COMMAND_WORKER_STRATEGY_GUARD_E2E_RESULT_V1

## 1. 结论

- `domain_command_worker.py` 当前已落库的 5 刀 strategy guard，已通过最小端到端验收。

## 2. 运行前提

- 仅执行 `docker compose up -d` 不足以带上最新源码。
- 本次验收前已执行：
  - `docker compose build backend worker`
  - `docker compose up -d backend worker`

## 3. 主线入口口径

- QUOTE 主线入口为：
  - `POST /domain-commands/quote`
- 请求体为：
  - 扁平 quote payload
- 本次不使用：
  - `POST /domain-commands` + `{"type":"quote","payload":{...}}`

## 4. 最小端到端验收结果

### 4.1 backend 健康检查

- `GET /health`
- 结果：HTTP 200
- 响应：`{"ok":true}`

### 4.2 top-level 命中样例

- command id：`quote-e8807911-047f-465e-96d4-6b534a28309e`
- status：`FAILED`
- reason/error：`TOP_LEVEL_FORBIDDEN_FIELD:exchange`
- 结论：PASS

### 4.3 nested 命中样例

- command id：`quote-d5d2cd12-51ab-4de0-89e9-859247ba8f50`
- status：`FAILED`
- reason/error：`NESTED_BYPASS_FORBIDDEN:bypass_risk`
- 结论：PASS

### 4.4 正常不命中样例

- command id：`quote-6b06c584-9037-4833-85b8-e914d027af54`
- status：`FAILED`
- reason/error：`RISK_HARD_LIMITS_STOP_REQUIRED:missing stop_loss or stop_price`
- 结论：PASS（不因 `TOP_LEVEL_FORBIDDEN_FIELD` / `NESTED_BYPASS_FORBIDDEN` 被拒）

## 5. 当前正式判断

- top-level forbidden guard：已真实生效
- nested bypass forbidden guard：已真实生效
- guard 未命中时：可继续进入后续既有风控链路
- 当前 5 刀已形成最小闭环，不应在无新验收目标前继续进入第六刀

## 6. 后续固定运维口径

- 改 backend / worker 代码后，应至少执行一次：
  - `docker compose build backend worker`
- 否则容器可能仍运行旧镜像，导致验收假阴性

## 7. 本轮不做什么

- 不新增第六刀
- 不修改 `domain_command_worker.py`
- 不修改 `policy_engine.py`
- 不推进实验目录

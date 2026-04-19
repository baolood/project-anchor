# DOMAIN_COMMAND_WORKER_STRATEGY_GUARD_ACCEPTANCE_V1

## 1. 目标

- 本文档只回答一个问题：
- 当前 `domain_command_worker.py` 已落库的 strategy guard 该如何做最小验收

## 2. 当前已落库事实

- `_risk_guard` 顶部已先调用 `_strategy_v1_top_payload_forbidden_field(payload)`
- 命中时返回：
  - `(False, f"TOP_LEVEL_FORBIDDEN_FIELD:{top_hit}")`
- 之后已调用 `_strategy_v1_command_payload_nested_bypass(payload)`
- 命中时返回：
  - `(False, f"NESTED_BYPASS_FORBIDDEN:{hit}")`
- 再之后为既有 `notional` / `RiskPolicyEngine` / `risk_guard` 路径

## 3. 最小验收范围

只验 3 类情况；**每类 1 个可复现样例即算覆盖**（样例仅作**结构**参考，键名须与代码中 **第一刀** `FORBIDDEN_FIELDS`、**第二刀** `_STRATEGY_V1_FORBIDDEN_BYPASS_KEYS` 一致）。

1. **top-level 命中**  
   - **条件**：`payload` **顶层** 出现 `FORBIDDEN_FIELDS` 中任一键（如 `exchange`、`api_key` 等，见 `domain_command_worker.py` 中 `FORBIDDEN_FIELDS` 定义）。  
   - **最小样例（JSON 形态）**：`{"exchange": "x"}`（或 `{ "api_key": "k" }` 等，**只含 1 个**禁止顶键即可）。  
   - **预期**：`risk_guard_fn` 失败且 `reason` 以 **`TOP_LEVEL_FORBIDDEN_FIELD:`** 为前缀，且冒号后为**命中的键名**（如 `TOP_LEVEL_FORBIDDEN_FIELD:exchange`）。

2. **nested bypass 命中**  
   - **条件**：`payload` 顶层 **不** 含 `FORBIDDEN_FIELDS` 中任一键，但 **嵌套** `dict` / `list`/`tuple` 结构中出现 **`_STRATEGY_V1_FORBIDDEN_BYPASS_KEYS`** 中任一键（如 `bypass_risk`、`skip_guard` 等）。  
   - **最小样例**：`{"intent_payload": {"bypass_risk": true}}` 或 `{"meta": [{"nested": {"skip_guard": 1}}]}`（任选其一结构能触发 nested 扫描即可）。  
   - **预期**：失败且 `reason` 以 **`NESTED_BYPASS_FORBIDDEN:`** 为前缀。

3. **正常不命中**  
   - **条件**：顶层 **无** `FORBIDDEN_FIELDS` 键；全文嵌套扫描 **无** bypass forbiden 键名。  
   - **最小样例**：`{}` 或 `{"notional_usd": 50}`（只要不包含上述两类禁止键）。  
   - **预期**：**不因**上述两类 guard 而返回 `TOP_LEVEL_*` / `NESTED_BYPASS_*`（命令可能在后续 **notional / RiskPolicyEngine / risk_guard** 或其它业务路径失败，但 **reason 不得** 以上述两类前缀开头）。

### 3.1 观测口径（任选其一即可 PASS）

- **端到端**：写入一条 `commands_domain` 命令（或通过既有 Console/API），使 worker 拾取执行；在 **worker 日志**、**domain 事件**、或 **对外返回体中带出的 failure reason** 中能读到对应前缀字符串。  
- **Runner 契约**：凡 **`risk_guard_fn`** 返回 `(False, reason)` 的路径，只要能证明 **`reason`** 字符串符合 §3 预期即可。

## 4. 明确不验什么

- 不扩展到 `_STRATEGY_V1_INTENT_KINDS`
- 不扩展到其它 worker 分支
- 不重做事件模型
- 不验证 mega WIP 中未落库逻辑
- 不修改 imports
- 不新增测试框架改造（本轮不要求 pytest 目录重构；若已有最小脚本仅追加断言则不在此禁止之列）

## 5. 最小通过标准

- 至少拿到 **2** 个明确拒绝样例：
  - **1** 个 **`TOP_LEVEL_FORBIDDEN_FIELD:*`**
  - **1** 个 **`NESTED_BYPASS_FORBIDDEN:*`**
- 至少拿到 **1** 个明确「**不因这两类 guard 拒绝**」样例（§3 第三类）
- 三类结果都能以 **日志 / 命令详情 reason / 事件负载** 直接判定 **PASS/FAIL**

## 6. 下一步执行边界

- 下一轮只允许围绕这 **3** 个验收样例做验证
- **不允许**直接进入第六刀代码扩展
- 若验收失败，先修正已落库五刀行为或观测链路，**不**新增新功能

## 7. 本轮不做什么

- 不修改 `domain_command_worker.py`
- 不提交 backend 代码
- 不恢复旧 WIP
- 不更新子模块

## 8. 证据锚点（代码）

- **`_risk_guard`**：`domain_worker_loop` 内约 **L738–751**（含 top-level → nested → 原有路径）

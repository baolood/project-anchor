# TRADE_GATE_DRY_RUN_ORDER_INTENT_V1

## 1. 任务结论

本文件定义 **`/trade-gate`（前端）→ dry-run order intent（契约）→ `commands_domain` 记录（后端只记不真下）** 的最小字段与状态规则。

目标：**Live-Ready Dry Run V1** — 使用真实订单字段格式、走真实执行入口（`domain_command_worker` / `order`），但 **仅** dry-run / testnet / paper；**不**触发真钱成交。

**本文件仅契约**；不修改 backend、worker、risk、workflow，不启用 live trading。

## 相关检查入口

- 负责人每日检查顺序：**`/ops` → `/commands` → `/commands/[id]`**（见 **`anchor-console`** 中 lead-check / ops 文档）。
- 活跃验收域：**`commands_domain` → `domain_command_worker` → terminal `DONE` / `FAILED`**；`order` 类型已覆盖 **BUY / SELL** 与 **RiskPolicyEngine / hard limits** 路径（实现细节以代码为准，本契约与之对齐）。
- Go-live：**R-001 OPEN**、§9 记录 **NO-GO**；CI 绿 ≠ 实盘许可。

---

## 2. 输入字段（Trade Gate → intent）

来源：用户在前端 **`/trade-gate`** 填写（本地 UI，无 API key）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `asset` | string | 交易标的符号，如 `BTC`；映射为执行层 `symbol`（当前 worker 样例为 `BTCUSDT`） |
| `direction` | enum | `BUY` \| `SELL` |
| `hypothetical_notional` | number \| string | 假设名义金额（USD 或项目约定单位）；映射为 `notional` |
| `entry_reason` | string | Q1：为什么要做这笔交易 |
| `exit_plan` | string | Q2：错了在哪里退出（须可检验：无效点 / 条件 / 亏损上限） |
| `emotional_state` | enum | `calm` \| `FOMO` \| `anxious` \| `revenge trading` \| `uncertain` |
| `gate_decision` | enum | UI 判定：`PAUSE` \| `SIMULATE_ONLY`（见 §4） |
| `gate_evaluated_at` | ISO-8601 | 闸门判定时间（UTC） |
| `source` | string | 固定 `trade_gate_v1` |

可选追溯（推荐，不落库敏感信息）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `client_session_id` | string | 匿名本地会话 id（非账户 id） |
| `copy_result_hash` | string | 可选：Copy result 内容哈希，便于审计对齐 |

**禁止作为输入：** 交易所 API key、账户 id、真实余额、真实持仓、用户身份信息。

---

## 3. 必填校验（闸门层）

在生成 **dry-run order intent** 之前，必须全部满足：

| # | 规则 | 失败时 |
|---|------|--------|
| 1 | `entry_reason` 去空白后非空 | `gate_decision` 强制 **PAUSE** |
| 2 | `exit_plan` 去空白后非空，且不得仅为「停止交易」等不可检验表述 | **PAUSE** |
| 3 | `emotional_state` 必须为 **`calm`** | **PAUSE** |
| 4 | `asset` 非空 | **PAUSE** |
| 5 | `direction` ∈ {`BUY`,`SELL`} | **PAUSE** |
| 6 | `hypothetical_notional` 可解析为 `> 0` 的数 | **PAUSE** |
| 7 | `exit_plan` 应包含至少一类可检验退出要素（无效点/价格或条件 **或** 明确最大可承受亏损上限） | 未满足则 **PAUSE**（实现可用启发式；V1 以人工填写质量为准） |

**风险字段（进入执行链时必填，映射到 command `payload`）：**

| 字段 | 映射到 payload | 说明 |
|------|----------------|------|
| `symbol` | `symbol` | 如 `BTCUSDT`（与现有 `OrderAction` 一致） |
| `side` | `side` | `BUY` / `SELL` |
| `notional` | `notional` | 正数 |
| `stop_loss` 或 `stop_price` | `stop_loss` / `stop_price` | 从 `exit_plan` 解析或单独字段；满足 hard limits **STOP_REQUIRED** |
| `exit_plan` | `exit_plan` | 原文保留，供审计 |

V1 若 UI 未单独采集 `stop_loss` 数值，**不得**进入 dry-run 入队；保持 **PAUSE** 直至补齐可映射的止损/无效点字段（后续 UI 迭代，非本文件实现范围）。

---

## 4. PAUSE / SIMULATE_ONLY → dry-run 转换规则

### 4.1 `PAUSE`

- **不** 创建 `commands_domain` 行。
- **不** 调用交易所、**不** 使用 API key。
- 仅允许写入 **gate 审计记录**（可选表/日志，V1 实现待定），状态：

```text
intent_status: REJECTED
reject_reason: GATE_PAUSE
```

- 对用户展示：停止；不下单；不进入 worker 队列。

### 4.2 `SIMULATE_ONLY`

- 表示：三问与情绪闸门通过，**仅** 允许生成 **dry-run order intent** 并进入记录/模拟执行链。
- **不等于** 许可真实下单或连接用户资金账户。

转换步骤（逻辑顺序）：

1. 应用 §3 校验；任一失败 → 按 **PAUSE** 处理。
2. 构建 **`DryRunOrderIntent`**（见 §5）。
3. 以 `execution_mode: "dry_run"` 写入后端（POST 契约 V1 未定义 URL；实现阶段对齐 `commands_domain` `type: "order"`）。
4. Worker 在 dry-run 模式下 **模拟** 执行：终端状态仍为 **`DONE`** 或 **`FAILED`**（与现有 worker 一致），**不** 产生真实成交。

### 4.3 与 `commands_domain` 状态对齐

| 层级 | 状态 | 含义 |
|------|------|------|
| Gate | `REJECTED` | PAUSE；未入队 |
| Gate | `ACCEPTED_FOR_DRY_RUN` | SIMULATE_ONLY 且通过 §3；已生成 intent |
| Command | `PENDING` | 已入队，待 worker pick |
| Command | `DONE` | dry-run 执行成功（模拟） |
| Command | `FAILED` | 校验/策略/执行失败（含 risk block） |

**`REJECTED`** 仅用于 **闸门拒绝**，不替代 worker 的 **`FAILED`**。

---

## 5. 后端记录格式（最小 payload）

建议 **`commands_domain`** 行（V1 对齐现有 `order` 类型）：

```json
{
  "type": "order",
  "status": "PENDING",
  "payload": {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "notional": 150,
    "stop_loss": 68500,
    "exit_plan": "If BTC breaks above 68500 (invalidation), or hypothetical loss reaches 3, exit simulation.",
    "execution_mode": "dry_run",
    "source": "trade_gate_v1",
    "gate_decision": "SIMULATE_ONLY",
    "entry_reason": "…",
    "emotional_state": "calm",
    "notional_usd": 150
  }
}
```

说明：

- `execution_mode` **必须**为 `"dry_run"` | `"testnet"` | `"paper"` 之一；V1 默认 **`dry_run`**。
- `notional` 与 `notional_usd` 可同时存在，供 **RiskPolicyEngine** / **hard_limits** 读取（与现有 risk 代码习惯对齐）。
- 实现前 **禁止** `execution_mode: "live"` 或缺省（缺省视为 **拒绝入队**）。

**DryRunOrderIntent**（逻辑对象，可序列化为上表 `payload` + 元数据）：

```text
intent_id: UUID
created_at: ISO-8601
execution_mode: dry_run
gate_decision: SIMULATE_ONLY
trade_fields: { symbol, side, notional, stop_loss|stop_price, exit_plan, entry_reason, emotional_state }
intent_status: ACCEPTED_FOR_DRY_RUN | REJECTED
```

---

## 6. 禁止真实下单边界（硬规则）

| # | 禁止项 |
|---|--------|
| 1 | 不得要求、存储、传输真实 **API key** 或交易所密钥 |
| 2 | 不得标记 `execution_mode: live` 或等价真钱执行 |
| 3 | 不得自动向交易所发送可成交订单（dry-run / testnet / paper 除外，且须显式模式） |
| 4 | 不得托管用户资金或采集真实资产余额 |
| 5 | 不得因 CI 绿或 Trade Gate **SIMULATE_ONLY** 宣称 go-live 已批准 |
| 6 | Worker 在 `dry_run` 下 **不得** 调用真实下单 HTTP（仅记录 + 模拟结果） |

违反上表 → 契约验收 **FAIL**，不得进入下一层 paper/testnet 自动化。

---

## 7. 推进链（本文件在链中的位置）

```text
Trade Gate (/trade-gate)
  ↓ 本文件：dry-run order intent 契约
  ↓ 实现：POST/入队 commands_domain（dry_run only）
  ↓ domain_command_worker：DONE / FAILED
  ↓ paper / testnet 执行层（后续）
  ↓ 风险验收
  ↓ 再谈真实 API（单独决策，非 V1）
```

---

## 8. 验收模板（契约文档）

```text
[Trade Gate -> Dry Run Intent Spec]

file created: PASS
only docs changed: PASS
defines input fields: PASS
defines required fields: PASS
defines PAUSE behavior: PASS
defines SIMULATE_ONLY -> dry-run intent behavior: PASS
defines no real API key: PASS
defines no real order: PASS
defines no fund custody: PASS
defines DONE / FAILED / REJECTED style result: PASS
does not modify backend: PASS
does not modify worker: PASS
does not modify risk: PASS
does not enable live trading: PASS

overall: PASS
```

---

## 9. 回滚方式

未提交：

```bash
cd /path/to/project-anchor
rm -f anchor-backend/docs/TRADE_GATE_DRY_RUN_ORDER_INTENT_V1.md
```

已提交：

```bash
git revert <commit>
git push origin main
```

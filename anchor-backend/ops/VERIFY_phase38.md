# Phase 3.8 — Risk State 接入 risk_gate / policy_engine（验收记录）

## 验证点
- risk_state / risk_state_history 为 Phase 3.7 key/value schema（含 key 列）
- POST /commands 在 risk_gate_global.enabled=true 时返回 403，detail 含 `RISK_GATE_GLOBAL`、`phase38_global_gate`
- risk_gate_global.enabled=false 后 POST /commands 返回 2xx 且响应含 `id`
- `ops/verify_phase38_risk_state_integration.sh` 全部通过（compat 模式）

## 证据路径
- `/tmp/anchor_phase38_verify_last.log`

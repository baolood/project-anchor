# Phase 3.8 — Risk State 接入 risk_gate / policy_engine（验收记录）

- Local: risk_state / risk_state_history 已切到 Phase 3.7 key/value schema（包含 key 列）
- API: POST /commands 在 gate ON 时返回 403，包含 `RISK_GATE_GLOBAL` 与 `phase38_global_gate`
- API: gate OFF 后 POST /commands 返回 2xx 并返回 `id`
- Script: `ops/verify_phase38_risk_state_integration.sh` PASS（compat）
- 证据：`/tmp/anchor_phase38_verify_last.log`

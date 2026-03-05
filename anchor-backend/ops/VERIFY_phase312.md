# Phase 3.12 — Observability Loop (risk_gate / policy / idempotency → ops_audit)

## Scope
- No schema changes. Uses existing `ops_audit`.
- `POST /commands` emits audit for:
  - Deny: KILL_SWITCH_ON / RISK_GATE_GLOBAL / MAX_SINGLE_TRADE_RISK
  - Conflict: IDEMPOTENCY_CONFLICT
  - Accept: COMMAND_CREATE_ACCEPTED

## Acceptance checks
1) Enable risk_gate_global → POST /commands denied 403, audit has COMMAND_CREATE_DENIED with code=RISK_GATE_GLOBAL  
2) policy_limits.max_single_trade_risk_usd=5 → POST risk_usd=8 denied 403, audit has COMMAND_CREATE_DENIED with code=MAX_SINGLE_TRADE_RISK  
3) Same idempotency key, different body → 409, audit has IDEMPOTENCY_CONFLICT with that key  
4) Normal create → 2xx, audit has COMMAND_CREATE_ACCEPTED with idempotency_key and command_id

## Evidence
- Verify log: `/tmp/anchor_phase312_observability_verify_20260305_221910.log`

## Result
- PASS

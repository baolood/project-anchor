# Phase 3.9 — 验收记录（single-trade risk limit）

## What changed
- `/commands` 在创建前接入：
  - risk_gate（check_create_command）
  - policy_engine async（risk_state.policy_limits + payload.risk_usd）

## Acceptance
- policy_limits.max_single_trade_risk_usd = 5
- risk_usd=3 → 2xx (ALLOW_OK)
- risk_usd=8 → 403, contains MAX_SINGLE_TRADE_RISK (DENY_LIMIT=YES)

## Evidence
- `/tmp/anchor_phase39_verify_last.log`（包含 ALLOW_OK / DENY_LIMIT=YES / PASS）

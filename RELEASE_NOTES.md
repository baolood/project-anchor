# Project Anchor — Risk Core v2

Tag: risk-core-v2  
Date: 2026-02-13  

---

## Scope

Risk Core v2 delivers:

- Daily Mode (default)
- Extreme Mode (optional gate)
- Hard Limits Layer (atomic exposure)
- Lockout Layer
- Risk Panel (UI)
- Unified E2E + Release Gate
- Stable evidence outputs under /tmp/anchor_*

---

## Modes

### Daily Mode (default)

- Hard limits enabled
- Atomic exposure enabled
- Extreme mode skipped
- Release must pass with PASS_OR_FAIL=PASS

Worker env (docker-compose.override.yml):

- CAPITAL_USD=1000
- MAX_SINGLE_TRADE_RISK_PCT=0.5
- MAX_NET_EXPOSURE_PCT=30
- MAX_LEVERAGE=5
- MAX_DAILY_DRAWDOWN_PCT=3
- RISK_HARD_LIMITS_DISABLE=0
- RISK_EXPOSURE_ATOMIC=1

---

### Extreme Mode (manual only)

- Enabled via EXTREME_MODE_E2E=1
- Runs burst stress test
- Generates:
  - /tmp/anchor_extreme_outcome_last.out
  - /tmp/anchor_extreme_daily_smoke_last.out
  - /tmp/anchor_extreme_risk_state_last.json

Default behavior: SKIPPED=YES

---

## Risk Layers

### 1. Lockout Layer
- Triggered by:
  - consecutive losses
  - daily loss pct threshold
- Emits RISK_LOCKOUT events
- Does NOT auto-toggle kill switch (UI advisory only)

### 2. Hard Limits Layer
- Single trade risk
- Net exposure
- Leverage
- Daily drawdown
- Stop required for QUOTE
- Atomic exposure guard (RISK_EXPOSURE_ATOMIC=1)

Failure emits:
- RISK_HARD_LIMITS_BLOCK
- Specific reason codes

---

## UI

Routes:

- /commands
- /risk
- /ops

Minimal usable console confirmed.

---

## E2E Coverage

Included in release:

- risk_hard_limits_e2e
- risk_lockout_block_e2e
- extreme_mode_e2e (default skipped)
- policy_block_explainer_e2e (stable; skipped when no sample)
- full verify_all_e2e
- release_up_and_verify.sh

Evidence paths:

- /tmp/anchor_e2e_release_up_and_verify_last.out
- /tmp/anchor_e2e_verify_all_release.out
- /tmp/anchor_e2e_index_last.out
- /tmp/anchor_e2e_checklist_*.out

---

## Release Status

release_up_and_verify.sh: PASS  
Tag: risk-core-v2  
Tag points to HEAD at time of release.

---

## Non-Goals

- No automatic kill-switch enforcement
- No strategy logic expansion
- No UI redesign beyond minimal usability
- No additional policy system

---

## Stability Guarantee

Daily Mode must:

- Start without manual export
- Pass release gate
- Allow compliant QUOTE
- Block non-compliant QUOTE
- Maintain atomic exposure correctness

Extreme Mode must:

- Not affect Daily release
- Be optional
- Produce deterministic outcome

# Real testnet review checklist V1

**Status:** review checklist only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** provide a short operator checklist for reviewing the future canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize real testnet execution. It only standardizes the manual review sequence.

## 1. Decision

This checklist applies only to:

```text
ORDER + execution_mode=testnet
```

Do not use it to approve:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
TESTNET_EXECUTOR_STUB
live trading
```

## 2. Review path

Always review in this order:

```text
/ops
-> /commands
-> /commands/[id]
```

Do not accept based on terminal output alone.

## 3. Pre-check

Before reviewing a command, confirm:

- `live trading: NO-GO`
- the command is intended as `ORDER + execution_mode=testnet`
- the review is not using legacy `QUOTE` evidence
- the review is not using stub-only evidence

If any of these fail, stop the review.

## 4. Canonical path check

At `/commands/[id]`, confirm:

- command is `ORDER`
- `payload.execution_mode` is `testnet`
- `source` is expected
- `created_by` is present
- `idempotency_key` is present

If path identity is unclear, mark review `FAIL`.

## 5. Final state check

Confirm final persisted state is one of:

- `DONE`
- `FAILED`

If state is unclear, missing, or not final, mark review `FAIL`.

## 6. Event chain check

Find the minimal event family and match it to one of these groups.

### Canonical success

Expected family:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_ACCEPTED
ACTION_OK
MARK_DONE
```

### Pre-external refusal

Expected family:

```text
PICKED
POLICY_ALLOW or POLICY_BLOCK
KILL_SWITCH_CHECKED when boundary-relevant
ACTION_FAIL
MARK_FAILED
```

### External-attempt failure

Expected family:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_REJECTED
ACTION_FAIL
MARK_FAILED
```

If the event family does not fit any approved group, mark review `FAIL`.

## 7. Failure or success family check

Map the result to one of the approved families.

Approved success:

- normalized canonical success result

Approved failure families:

- `TESTNET_CONTRACT_REJECTED`
- `POLICY_BLOCK`
- `RISK_HARD_LIMITS_...`
- `KILL_SWITCH_ON`
- `TESTNET_CREDENTIALS_MISSING`
- `TESTNET_BASE_URL_INVALID`
- `TESTNET_EXECUTOR_AUTH_FAILED`
- `TESTNET_EXECUTOR_VALIDATION_FAILED`
- `TESTNET_EXECUTOR_REJECTED`
- `TESTNET_EXECUTOR_TIMEOUT`
- `TESTNET_EXECUTOR_NETWORK_ERROR`
- `TESTNET_EXECUTOR_UNEXPECTED`

If the family is vague or missing, mark review `FAIL`.

## 8. External request status check

Classify the command as exactly one of:

- `no`
- `attempted`
- `accepted`

Use this rule:

- contract/policy/risk/kill-switch/credentials/base-url failures => `no`
- auth/validation/rejected/timeout/network/unexpected executor failures => `attempted`
- canonical success => `accepted`

If external request status is ambiguous, mark review `FAIL`.

## 9. Negative evidence check

### For pre-external failures

Confirm these are absent:

- `TESTNET_EXECUTOR_ACCEPTED`
- `ACTION_OK`
- `MARK_DONE`
- `external_order_id`
- `external_status` from real upstream

### For kill switch refusal

Also confirm:

- `TESTNET_EXECUTOR_REQUESTED` is absent after refusal

### For all canonical real reviews

Do not accept:

- `TESTNET_EXECUTOR_STUB` as real evidence

If negative evidence fails, mark review `FAIL`.

## 10. Reviewer questions

Before accepting, answer all of these:

1. Was this the canonical `ORDER + execution_mode=testnet` path?
2. What is the final state?
3. Which event family appeared?
4. Which normalized success/failure family applies?
5. Was an external request blocked, attempted, or accepted?
6. Is there any evidence of live-path contamination?

If any answer is unclear, the review is not acceptable.

## 11. Fast PASS rules

Mark review `PASS` only if all are true:

- canonical path confirmed
- final state is final and reviewable
- event family matches an approved group
- success/failure family is approved
- external request status is clear
- negative evidence checks pass
- no legacy QUOTE path evidence
- no stub-only acceptance evidence
- no live trading implication

## 12. Fast FAIL rules

Mark review `FAIL` if any are true:

- path identity unclear
- final state unclear
- event family incomplete or off-contract
- failure family missing or vague
- external request status ambiguous
- kill switch proof unclear
- live-path contamination suspected
- legacy QUOTE path used
- stub evidence used as real proof

## 13. What this checklist does not do

- It does not approve rollout by itself.
- It does not replace the smoke spec.
- It does not replace the failure taxonomy.
- It does not replace the evidence matrix.
- It does not authorize live trading.

## 14. Relationship to adjacent docs

This checklist compresses:

- [docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md)
- [docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md)
- [docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md](/Users/baolood/Projects/project-anchor/docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md)
- [docs/REAL_TESTNET_SMOKE_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_SMOKE_SPEC_V1.md)

## 15. Recommended next bounded round

After this checklist, the natural next round is:

```text
Real Testnet Operator Runbook V1
```

Scope:

```text
docs-only
turn checklist + matrix into a single operator run sequence
no real key
no live trading
```

## 16. Acceptance for this checklist

```text
canonical review checklist fixed for ORDER + execution_mode=testnet: PASS
review path fixed to /ops -> /commands -> /commands/[id]: PASS
approved event groups stated: PASS
approved failure families stated: PASS
negative evidence checks stated: PASS
stub evidence excluded: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

# Real testnet operator runbook V1

**Status:** operator runbook only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** define the operator review flow for the future canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This runbook does not authorize real testnet execution. It standardizes how an operator should review and classify evidence once such a path exists.

## 1. Decision

This runbook is valid only for:

```text
ORDER + execution_mode=testnet
```

Do not use it to approve:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
TESTNET_EXECUTOR_STUB
live trading
```

## 2. What this runbook is for

This runbook exists to make one workflow repeatable:

```text
open review path
identify canonical path
classify state
classify event family
classify success/failure family
classify external request status
check negative evidence
record PASS or FAIL
```

The goal is to remove guesswork and reduce review drift.

## 3. Fixed review path

Always review in this order:

```text
/ops
-> /commands
-> /commands/[id]
```

Do not finalize review from terminal output alone.

## 4. Stop conditions before review

Stop immediately if any of these are true:

- `live trading: NO-GO` is not being respected
- command is not clearly `ORDER + execution_mode=testnet`
- evidence comes from legacy `QUOTE` path
- evidence comes from stub-only path
- final command detail cannot be opened

If any stop condition triggers, record:

```text
review blocked
canonical evidence not established
```

## 5. Operator sequence

Run the review in this exact order.

### Step 1. Confirm path identity

At `/commands/[id]`, confirm:

- command type is `ORDER`
- `payload.execution_mode` is `testnet`
- `source` is present and expected
- `created_by` is present
- `idempotency_key` is present

If path identity is unclear, stop and mark `FAIL`.

### Step 2. Confirm final state

Record final state as:

- `DONE`
- `FAILED`

If state is not final or not visible, stop and mark `FAIL`.

### Step 3. Match event family

Match the event chain to one of:

- canonical success
- pre-external refusal
- external-attempt failure

If event family does not fit one of these, stop and mark `FAIL`.

### Step 4. Match normalized family

Classify result into one approved family.

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

Approved success:

- normalized canonical success result

If family is vague or missing, stop and mark `FAIL`.

### Step 5. Classify external request status

Choose exactly one:

- `no`
- `attempted`
- `accepted`

Use this mapping:

- contract/policy/risk/kill-switch/credentials/base-url => `no`
- auth/validation/rejected/timeout/network/unexpected => `attempted`
- canonical success => `accepted`

If classification is ambiguous, stop and mark `FAIL`.

### Step 6. Check negative evidence

For pre-external failures, confirm absence of:

- `TESTNET_EXECUTOR_ACCEPTED`
- `ACTION_OK`
- `MARK_DONE`
- `external_order_id`
- `external_status` from real upstream

For kill switch refusal, also confirm:

- `TESTNET_EXECUTOR_REQUESTED` is absent after refusal

For all canonical real review:

- do not accept `TESTNET_EXECUTOR_STUB` as proof

If any negative evidence check fails, stop and mark `FAIL`.

### Step 7. Record review result

Record one of:

```text
PASS
FAIL
BLOCKED
```

Use:

- `PASS` only when all checks are satisfied
- `FAIL` when evidence contradicts contract
- `BLOCKED` when evidence is missing or review path unavailable

## 6. Minimal evidence families

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

## 7. Fast scenario mapping

Use this mapping during review:

| Scenario | Expected state | External request status | Key reviewer question |
|---|---|---:|---|
| Canonical success | `DONE` | accepted | Did the canonical ORDER testnet path reach upstream and return reviewable success without touching live? |
| Contract rejection | `FAILED` | no | Was the payload rejected locally before any external request? |
| Policy block | `FAILED` | no | Did policy guardrails intentionally block this before execution? |
| Risk hard-limit block | `FAILED` | no | Did risk hard limits stop this before any external request? |
| Kill switch refusal | `FAILED` | no | Is there proof kill switch blocked at the boundary and no signed HTTP happened after that? |
| Missing credentials | `FAILED` | no | Were canonical `TESTNET_EXCHANGE_*` credentials unavailable before request attempt? |
| Invalid base URL | `FAILED` | no | Was execution refused because the host/config was not clearly testnet-safe? |
| Upstream auth failure | `FAILED` | attempted | Did a signed request reach upstream and fail for auth/scope reasons? |
| Upstream validation failure | `FAILED` | attempted | Was local contract accepted but upstream rejected request semantics? |
| Upstream business rejection | `FAILED` | attempted | Did upstream reject for a business reason that is not auth or validation? |
| Timeout | `FAILED` | attempted | Did the request attempt fail to complete in time? |
| Network error | `FAILED` | attempted | Did the transport fail before a clear upstream application result? |
| Unexpected executor failure | `FAILED` | attempted or unknown | Is this an uncategorized executor failure that needs manual triage? |

## 8. Operator notes

- `PASS` does not mean live trading approval.
- `DONE` does not mean go-live approval.
- A correct `FAILED` can still be a successful review outcome if it matches the expected family.
- Kill switch proof is especially sensitive: if boundary placement is unclear, do not guess.

## 9. What not to do

- Do not approve from terminal output alone.
- Do not skip path identity confirmation.
- Do not collapse all failures into generic `FAILED`.
- Do not treat stub evidence as real executor proof.
- Do not use this runbook to justify live execution.

## 10. Relationship to adjacent docs

This runbook operationalizes:

- [docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md)
- [docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md)
- [docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md)
- [docs/REAL_TESTNET_SMOKE_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_SMOKE_SPEC_V1.md)

## 11. Recommended next bounded round

After this runbook, the natural next round is:

```text
Real Testnet Readiness Bundle Index V1
```

Scope:

```text
docs-only
create a single index that links the full real-testnet review stack in order
no real key
no live trading
```

## 12. Acceptance for this runbook

```text
canonical operator run sequence fixed for ORDER + execution_mode=testnet: PASS
review path fixed to /ops -> /commands -> /commands/[id]: PASS
stop conditions stated: PASS
PASS/FAIL/BLOCKED recording rule stated: PASS
negative evidence checks stated: PASS
stub evidence excluded: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

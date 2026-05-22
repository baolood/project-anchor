# Real testnet evidence matrix V1

**Status:** review matrix only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** compress the future canonical real testnet review evidence into one matrix for:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement real testnet execution. It standardizes what reviewers must inspect when verifying command outcomes.

## 1. Decision

The evidence matrix applies only to:

```text
ORDER + execution_mode=testnet
```

It does not accept evidence from:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
TESTNET_EXECUTOR_STUB
```

as canonical proof of future real testnet behavior.

## 2. Objective

The matrix exists to answer one operational need:

```text
given a command detail page,
can a reviewer quickly tell
what path ran,
what event family appeared,
what failure/success family it maps to,
and whether the result is acceptable evidence?
```

Without this compression layer, review depends too much on memory across multiple docs.

## 3. Fixed review path

Human review remains:

```text
/ops
-> /commands
-> /commands/[id]
```

Terminal output can support triage, but final acceptance must be possible from command detail evidence.

## 4. Core review columns

Every real testnet review should answer these columns:

| Column | Meaning |
|---|---|
| Command state | final persisted state, e.g. `DONE` / `FAILED` |
| Event family | minimal event chain visible in review |
| Failure/success family | normalized meaning, e.g. `KILL_SWITCH_ON` |
| External request status | `no`, `attempted`, or `accepted` |
| Reviewer question | the one thing the reviewer must confirm |

## 5. Evidence matrix

| Scenario | Command state | Event family | Failure/success family | External request status | Reviewer question |
|---|---|---|---|---|---|
| Canonical success | `DONE` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_ACCEPTED -> ACTION_OK -> MARK_DONE` | normalized success result | accepted | Did the canonical ORDER testnet path reach upstream and return reviewable success without touching live? |
| Contract rejection | `FAILED` | `PICKED -> ACTION_FAIL -> MARK_FAILED` or `PICKED -> POLICY_ALLOW -> ACTION_FAIL -> MARK_FAILED` | `TESTNET_CONTRACT_REJECTED` | no | Was the payload rejected locally before any external request? |
| Policy block | `FAILED` | `PICKED -> POLICY_BLOCK -> MARK_FAILED` | `POLICY_BLOCK` | no | Did policy guardrails intentionally block this before execution? |
| Risk hard-limit block | `FAILED` | `PICKED -> POLICY_ALLOW -> ACTION_FAIL -> MARK_FAILED` | `RISK_HARD_LIMITS_...` | no | Did risk hard limits stop this before any external request? |
| Kill switch refusal | `FAILED` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> ACTION_FAIL -> MARK_FAILED` | `KILL_SWITCH_ON` | no | Is there proof kill switch blocked at the boundary and no signed HTTP happened after that? |
| Missing credentials | `FAILED` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> ACTION_FAIL -> MARK_FAILED` | `TESTNET_CREDENTIALS_MISSING` | no | Were canonical `TESTNET_EXCHANGE_*` credentials unavailable before request attempt? |
| Invalid base URL | `FAILED` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> ACTION_FAIL -> MARK_FAILED` | `TESTNET_BASE_URL_INVALID` | no | Was execution refused because the host/config was not clearly testnet-safe? |
| Upstream auth failure | `FAILED` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_REJECTED -> ACTION_FAIL -> MARK_FAILED` | `TESTNET_EXECUTOR_AUTH_FAILED` | attempted | Did a signed request reach upstream and fail for auth/scope reasons? |
| Upstream validation failure | `FAILED` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_REJECTED -> ACTION_FAIL -> MARK_FAILED` | `TESTNET_EXECUTOR_VALIDATION_FAILED` | attempted | Was local contract accepted but upstream rejected request semantics? |
| Upstream business rejection | `FAILED` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_REJECTED -> ACTION_FAIL -> MARK_FAILED` | `TESTNET_EXECUTOR_REJECTED` | attempted | Did upstream reject for a business reason that is not auth or validation? |
| Timeout | `FAILED` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_REJECTED -> ACTION_FAIL -> MARK_FAILED` | `TESTNET_EXECUTOR_TIMEOUT` | attempted | Did the request attempt fail to complete in time? |
| Network error | `FAILED` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_REJECTED -> ACTION_FAIL -> MARK_FAILED` | `TESTNET_EXECUTOR_NETWORK_ERROR` | attempted | Did the transport fail before a clear upstream application result? |
| Unexpected executor failure | `FAILED` | `PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_REJECTED -> ACTION_FAIL -> MARK_FAILED` | `TESTNET_EXECUTOR_UNEXPECTED` | attempted or unknown | Is this an uncategorized executor failure that needs manual triage? |

## 6. Negative evidence guardrails

Reviewers must also check what is **absent**.

### For pre-external failures

These scenarios must **not** show:

```text
TESTNET_EXECUTOR_ACCEPTED
ACTION_OK
MARK_DONE
external_order_id
external_status from real upstream
```

Applies to:

```text
TESTNET_CONTRACT_REJECTED
POLICY_BLOCK
RISK_HARD_LIMITS_...
KILL_SWITCH_ON
TESTNET_CREDENTIALS_MISSING
TESTNET_BASE_URL_INVALID
```

### For kill switch refusal specifically

These must also be absent:

```text
TESTNET_EXECUTOR_REQUESTED after refusal
```

because the whole point is proving safe refusal before signed HTTP.

### For canonical real review in general

This must not be used as acceptance evidence:

```text
TESTNET_EXECUTOR_STUB
```

## 7. Fast review questions

When looking at `/commands/[id]`, reviewers should ask in order:

1. Was this the canonical `ORDER + execution_mode=testnet` path?
2. Is the final state `DONE` or `FAILED`?
3. Which event family appeared?
4. Which normalized success/failure family does it map to?
5. Was an external request blocked, attempted, or accepted?
6. Is there any evidence of live-path contamination?

If any answer is unclear, the review is not yet acceptable.

## 8. PASS use of this matrix

The matrix is being used correctly only if:

```text
review starts from command detail evidence
canonical path is confirmed first
state/event/failure/external-request columns are all checked
pre-external failures are not mistaken for upstream failures
stub evidence is not used as real executor proof
live trading remains NO-GO
```

## 9. What this matrix does not do

- It does not approve real testnet rollout by itself.
- It does not replace the smoke spec.
- It does not replace the kill switch boundary proof.
- It does not replace the failure taxonomy.
- It does not authorize live trading.

## 10. Relationship to adjacent docs

This matrix compresses evidence from:

- [docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md)
- [docs/REAL_TESTNET_SMOKE_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_SMOKE_SPEC_V1.md)
- [docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md](/Users/baolood/Projects/project-anchor/docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md)
- [docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md](/Users/baolood/Projects/project-anchor/docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md)

## 11. Recommended next bounded round

After this matrix, the natural next round is:

```text
Real Testnet Review Checklist V1
```

Scope:

```text
docs-only
convert the matrix into a short operator checklist
no real key
no live trading
```

## 12. Acceptance for this matrix

```text
canonical review matrix fixed for ORDER + execution_mode=testnet: PASS
state/event/failure/external-request columns stated: PASS
negative evidence guardrails stated: PASS
stub evidence excluded: PASS
review path fixed to /ops -> /commands -> /commands/[id]: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

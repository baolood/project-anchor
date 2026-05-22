# Real testnet failure taxonomy V1

**Status:** taxonomy design only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** define the stable failure families for the future canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement new failures. It fixes the vocabulary reviewers and future implementation should use.

## 1. Decision

The canonical failure taxonomy belongs only to:

```text
ORDER + execution_mode=testnet
```

It must not be designed around:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
```

It must not treat stub-only outcomes as real external failure proof.

## 2. Objective

The taxonomy exists to solve one practical problem:

```text
when a real testnet attempt fails,
reviewers must be able to tell quickly
which layer failed,
whether any external request was sent,
and whether the failure was safe
```

Without a fixed taxonomy, command detail review becomes ambiguous and incident handling drifts.

## 3. Design rules

The taxonomy must follow these rules:

- each failure family points to one primary layer
- failure family names must be stable and machine-readable
- failure family names must be specific enough for review, but not depend on raw upstream wording
- local validation failures must be distinguishable from upstream failures
- kill switch refusal must be distinguishable from policy/risk refusal
- timeout/network failures must be distinguishable from upstream business rejection

## 4. Primary failure layers

The canonical ORDER testnet path should classify failures into these layers:

```text
contract
policy
risk
kill_switch
credentials
base_url
upstream_auth
upstream_validation
upstream_rejection
timeout
network
unexpected
```

These layers are review-facing categories, not a promise that every internal exception becomes a unique external code.

## 5. Canonical failure families

Recommended stable failure families:

```text
TESTNET_CONTRACT_REJECTED
POLICY_BLOCK
RISK_HARD_LIMITS_...
KILL_SWITCH_ON
TESTNET_CREDENTIALS_MISSING
TESTNET_BASE_URL_INVALID
TESTNET_EXECUTOR_AUTH_FAILED
TESTNET_EXECUTOR_VALIDATION_FAILED
TESTNET_EXECUTOR_REJECTED
TESTNET_EXECUTOR_TIMEOUT
TESTNET_EXECUTOR_NETWORK_ERROR
TESTNET_EXECUTOR_UNEXPECTED
```

Notes:

- `RISK_HARD_LIMITS_...` intentionally preserves the existing detailed suffix pattern.
- `TESTNET_EXECUTOR_REJECTED` is for upstream business rejection that is not better classified as auth or validation.
- `TESTNET_EXECUTOR_UNEXPECTED` is a last-resort catch-all, not the preferred steady-state outcome.

## 6. Family-to-layer mapping

| Failure family | Primary layer | External request sent? | Reviewer meaning |
|---|---|---:|---|
| `TESTNET_CONTRACT_REJECTED` | contract | no | payload shape or required field problem |
| `POLICY_BLOCK` | policy | no | policy guardrail blocked execution |
| `RISK_HARD_LIMITS_...` | risk | no | hard risk limit blocked execution |
| `KILL_SWITCH_ON` | kill_switch | no | kill switch refused before signed HTTP |
| `TESTNET_CREDENTIALS_MISSING` | credentials | no | canonical testnet credentials absent |
| `TESTNET_BASE_URL_INVALID` | base_url | no | host/config not clearly testnet-safe |
| `TESTNET_EXECUTOR_AUTH_FAILED` | upstream_auth | yes | signed request reached upstream but auth failed |
| `TESTNET_EXECUTOR_VALIDATION_FAILED` | upstream_validation | yes | upstream rejected field/value semantics |
| `TESTNET_EXECUTOR_REJECTED` | upstream_rejection | yes | upstream rejected for another business reason |
| `TESTNET_EXECUTOR_TIMEOUT` | timeout | attempted | request attempt did not complete in time |
| `TESTNET_EXECUTOR_NETWORK_ERROR` | network | attempted | transport/DNS/TLS/connectivity failure |
| `TESTNET_EXECUTOR_UNEXPECTED` | unexpected | unknown/maybe | unexpected executor failure; investigate |

## 7. Event expectations by family

Minimum expected evidence families:

### Local pre-external failures

For:

```text
TESTNET_CONTRACT_REJECTED
POLICY_BLOCK
RISK_HARD_LIMITS_...
KILL_SWITCH_ON
TESTNET_CREDENTIALS_MISSING
TESTNET_BASE_URL_INVALID
```

the event chain must not imply external acceptance.

Expected family:

```text
PICKED
POLICY_ALLOW or POLICY_BLOCK
KILL_SWITCH_CHECKED when boundary-relevant
ACTION_FAIL
MARK_FAILED
```

No `TESTNET_EXECUTOR_ACCEPTED` should appear.

### External-attempt failures

For:

```text
TESTNET_EXECUTOR_AUTH_FAILED
TESTNET_EXECUTOR_VALIDATION_FAILED
TESTNET_EXECUTOR_REJECTED
TESTNET_EXECUTOR_TIMEOUT
TESTNET_EXECUTOR_NETWORK_ERROR
TESTNET_EXECUTOR_UNEXPECTED
```

expected family:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_REJECTED
ACTION_FAIL
MARK_FAILED
```

The taxonomy does not require a unique event name for every failure family, but the normalized error/result must preserve the specific family.

## 8. What each family must let reviewers answer

At `/commands/[id]`, a reviewer should be able to answer:

### `TESTNET_CONTRACT_REJECTED`

```text
which required field or shape failed?
was this blocked before any external request?
```

### `POLICY_BLOCK`

```text
which policy guardrail blocked execution?
was this a deliberate non-risk governance block?
```

### `RISK_HARD_LIMITS_...`

```text
which hard limit fired?
was the refusal expected from current risk policy?
```

### `KILL_SWITCH_ON`

```text
was the kill switch checked at the right boundary?
is there proof no signed HTTP happened afterward?
```

### `TESTNET_CREDENTIALS_MISSING`

```text
were canonical TESTNET_EXCHANGE_* credentials unavailable?
was this blocked before external request?
```

### `TESTNET_BASE_URL_INVALID`

```text
was the configured host ambiguous or non-testnet?
was execution refused before signed HTTP?
```

### `TESTNET_EXECUTOR_AUTH_FAILED`

```text
did upstream reject authentication after a signed request?
is the issue key/secret/scope-related rather than payload shape?
```

### `TESTNET_EXECUTOR_VALIDATION_FAILED`

```text
did upstream reject the request semantics?
was the local contract accepted but upstream contract stricter?
```

### `TESTNET_EXECUTOR_REJECTED`

```text
did upstream reject the order for a business reason that is not auth/validation?
```

### `TESTNET_EXECUTOR_TIMEOUT`

```text
did we attempt external contact but fail to receive a timely result?
```

### `TESTNET_EXECUTOR_NETWORK_ERROR`

```text
did the transport fail before a clear upstream application response?
```

### `TESTNET_EXECUTOR_UNEXPECTED`

```text
did an uncategorized executor failure happen that needs manual triage?
```

## 9. Normalization guidance

The normalized failure representation should preserve:

```text
failure_family
failure_reason
execution_mode=testnet
command_id
idempotency_key
source
created_by
ts
```

When safe and non-secret, it may also preserve:

```text
upstream_status_code
upstream_error_class
network_stage
host_label
```

Do not normalize raw secrets, signatures, or plaintext credentials into command results.

## 10. Review anti-patterns

Do not do these:

- collapse all upstream failures into one vague `FAILED`
- reuse `TESTNET_EXECUTOR_STUB` as a real failure hint
- classify `KILL_SWITCH_ON` as network or policy noise
- classify upstream auth problems as local contract failure
- leak raw upstream secret-bearing diagnostics into review output

## 11. PASS criteria for future implementation

Future real testnet implementation should only be considered taxonomy-aligned if:

```text
canonical failure families are used consistently
local vs external failures are distinguishable
kill switch refusal remains explicit
timeout and network are not collapsed into generic rejection
/commands/[id] shows enough evidence for review
no live trading path is implied
```

## 12. Relationship to adjacent docs

This taxonomy works with:

- [docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md](/Users/baolood/Projects/project-anchor/docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md)
- [docs/REAL_TESTNET_SMOKE_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_SMOKE_SPEC_V1.md)
- [docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md](/Users/baolood/Projects/project-anchor/docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md)
- [docs/TESTNET_COMMAND_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_COMMAND_CONTRACT_V1.md)

It does not replace them. It standardizes the failure vocabulary they rely on.

## 13. Recommended next bounded round

After this taxonomy, the natural next round is:

```text
Real Testnet Evidence Matrix V1
```

Scope:

```text
docs-only
cross-map command state, event chain, failure family, and reviewer questions
no real key
no live trading
```

## 14. Acceptance for this taxonomy

```text
canonical failure families fixed for ORDER + execution_mode=testnet: PASS
local vs external failure split stated: PASS
kill switch family explicit: PASS
timeout/network/auth/validation vocabulary fixed: PASS
stub evidence excluded from real taxonomy: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

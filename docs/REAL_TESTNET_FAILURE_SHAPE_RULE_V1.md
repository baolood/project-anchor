# Real testnet failure shape rule V1

**Status:** failure-shape rule only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Security lead, interim).

**Date:** 2026-05-22

**Scope:** define which normalized fields are mandatory for a FAIL-worthy real upstream failure result on the future canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement failure normalization. It fixes what “good enough to accept as a real upstream failure shape” means.

## 1. Decision

A canonical real testnet failure result is FAIL-worthy only if it contains a minimum normalized field set that proves:

```text
canonical ORDER path ran
failure family is reviewable
external-request status can be inferred
the result is safe and non-secret
```

Anything less than that is not an accepted failure shape.

## 2. Why this rule exists

Without a fixed failure shape, a command can land in `FAILED` but still be too vague to review correctly.

This rule answers:

```text
what exact fields must exist before a FAILED result can be treated as acceptable real external failure evidence?
```

## 3. Required failure fields

A FAIL-worthy normalized real testnet failure must include all of these fields:

```text
ok
type
execution_mode
market
symbol
side
order_type
source
created_by
idempotency_key
host_label
failure_family
failure_reason
ts
```

If any required field is missing, failure is not sufficiently reviewable.

## 4. Required field meanings

| Field | Required meaning |
|---|---|
| `ok` | must be `false` |
| `type` | must reflect canonical order semantics |
| `execution_mode` | must be `testnet` |
| `market` | canonical market label, e.g. `binance_testnet` |
| `symbol` | reviewed symbol |
| `side` | BUY / SELL |
| `order_type` | market / limit / other accepted order mode |
| `source` | command origin |
| `created_by` | operator or system initiator |
| `idempotency_key` | original logical command replay key |
| `host_label` | named venue host profile label or safe-fail host label |
| `failure_family` | canonical failure taxonomy family |
| `failure_reason` | human-comprehensible normalized reason |
| `ts` | normalized failure timestamp |

## 5. Minimum semantic rules

### `ok`

Must be:

```text
false
```

Anything else is not a failure shape.

### `execution_mode`

Must be:

```text
testnet
```

If failure is recorded with a different execution mode, the review is invalid.

### `failure_family`

Must be:

```text
present
non-empty
one of the approved canonical families
```

Approved families currently include:

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

### `failure_reason`

Must be:

```text
present
non-empty
human-comprehensible
non-secret
```

It does not need to mirror raw upstream text exactly, but it must explain the normalized failure meaning well enough for review.

### `host_label`

Must be present even for failure, because review still needs to know:

```text
which venue profile or host-safety label this failure belongs to
```

For pre-external failures, `host_label` may still reflect the selected canonical venue profile rather than a completed upstream contact.

## 6. Recommended optional fields

These are not mandatory for FAIL, but strongly recommended:

```text
attempt
upstream_status_code
upstream_error_class
timeout_stage
network_stage
external_request_status
```

Why they help:

- make failure-family review faster
- strengthen incident triage
- reduce ambiguity between attempted and non-attempted failures

## 7. What is not acceptable as failure

The following are **not** FAIL-worthy failure shapes:

- `FAILED` without `failure_family`
- `FAILED` without `failure_reason`
- `FAILED` without `execution_mode=testnet`
- `FAILED` without `host_label`
- `FAILED` that cannot be tied back to `source` and `created_by`
- `FAILED` that omits `idempotency_key`
- `FAILED` with secret-bearing raw diagnostics as the only explanation

These outcomes are too weak or unsafe for canonical review.

## 8. Relationship to failure families

The failure shape does not replace the taxonomy. It must point into it.

Meaning:

```text
failure_family answers “what kind of failure?”
failure_reason answers “what happened in reviewable words?”
```

Both are required.

## 9. Relationship to event evidence

If failure is canonical and reviewable, the event family should also agree.

Pre-external failures should line up with:

```text
PICKED
POLICY_ALLOW or POLICY_BLOCK
KILL_SWITCH_CHECKED when boundary-relevant
ACTION_FAIL
MARK_FAILED
```

External-attempt failures should line up with:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_REJECTED
ACTION_FAIL
MARK_FAILED
```

The failure shape does not replace the event chain.
Both must agree.

## 10. Relationship to external-request status

The failure shape should support reviewer inference about whether a real external request happened.

Minimum rule:

- pre-external families must not imply accepted upstream contact
- external-attempt families must be distinguishable from local refusal families

If this cannot be inferred from family plus surrounding evidence, the failure shape is too weak.

## 11. Review questions this shape must answer

At `/commands/[id]`, a reviewer should be able to answer:

- was this the canonical `ORDER + execution_mode=testnet` path?
- what failure family applies?
- what normalized reason explains it?
- which venue profile or host label was involved?
- who initiated the command?
- what replay key ties this failure back to the intended command?

If any answer is unavailable, the failure shape is incomplete.

## 12. Field integrity rules

The normalized failure shape must not:

- leak secrets
- include API keys
- include request signatures
- include raw auth headers
- rely on raw upstream dumps to be understandable

The goal is:

```text
reviewable, stable, non-secret failure evidence
```

## 13. Relationship to adjacent docs

This rule aligns with:

- [docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md)
- [docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md)
- [docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md)
- [docs/REAL_TESTNET_OPEN_QUESTIONS_REGISTER_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPEN_QUESTIONS_REGISTER_V1.md)

It resolves Q-006 at the failure-shape level.

## 14. What not to do

- Do not accept `FAILED` with vague payload.
- Do not treat event evidence alone as enough if failure shape is weak.
- Do not hide missing `failure_family` behind generic “rejected”.
- Do not let pre-external and external-attempt failures collapse into the same vague shape.
- Do not introduce live-trading semantics into this shape.

## 15. Recommended next bounded round

After this rule, the natural next round is:

```text
Real Testnet Timeout Policy Rule V1
```

Scope:

```text
docs-only
resolve the first canonical timeout and retry posture for real testnet executor attempts
no real key
no live trading
```

## 16. Acceptance for this rule

```text
FAIL-worthy real failure field set fixed: PASS
failure_family required: PASS
failure_reason required: PASS
host_label required: PASS
execution_mode=testnet required: PASS
idempotency_key required: PASS
non-secret integrity rule stated: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

# Real testnet success shape rule V1

**Status:** success-shape rule only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Security lead, interim).

**Date:** 2026-05-22

**Scope:** define which normalized fields are mandatory for a PASS-worthy real upstream success result on the future canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement success normalization. It fixes what “good enough to accept as real upstream success” means.

## 1. Decision

A canonical real testnet success result is PASS-worthy only if it contains a minimum normalized field set that proves:

```text
canonical ORDER path ran
real upstream accepted
the result is reviewable at /commands/[id]
no live-path ambiguity exists
```

Anything less than that is not an accepted success shape.

## 2. Why this rule exists

Without a fixed success shape, a command could land in `DONE` but still be too vague to trust.

This rule answers:

```text
what exact fields must exist before a DONE result can be treated as real external success evidence?
```

## 3. Required success fields

A PASS-worthy normalized real testnet success must include all of these fields:

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
external_order_id
external_status
ts
```

If any required field is missing, success is not sufficiently reviewable.

## 4. Required field meanings

| Field | Required meaning |
|---|---|
| `ok` | must be `true` |
| `type` | must reflect canonical order semantics |
| `execution_mode` | must be `testnet` |
| `market` | canonical market label, e.g. `binance_testnet` |
| `symbol` | reviewed symbol |
| `side` | BUY / SELL |
| `order_type` | market / limit / other accepted order mode |
| `source` | command origin |
| `created_by` | operator or system initiator |
| `idempotency_key` | original logical command replay key |
| `host_label` | named venue host profile label |
| `external_order_id` | real upstream acceptance identifier |
| `external_status` | normalized upstream acceptance status |
| `ts` | normalized success timestamp |

## 5. Minimum semantic rules

### `ok`

Must be:

```text
true
```

Anything else is not a success shape.

### `execution_mode`

Must be:

```text
testnet
```

If success is recorded with a different execution mode, the review is invalid.

### `external_order_id`

Must be:

```text
present
non-empty
derived from real upstream acceptance
```

This is one of the core proofs that the result is not just a local stub or fake local success.

### `external_status`

Must be:

```text
present
non-empty
normalized enough for operator review
```

It does not need to preserve every raw upstream nuance, but it must indicate accepted upstream state.

### `host_label`

Must map to the named venue profile selected by host-safety validation.

This helps prove that:

```text
the accepted result belongs to the approved testnet venue
```

## 6. Recommended optional fields

These are not mandatory for PASS, but strongly recommended:

```text
notional
stop_price
venue_order_type
accepted_ts
upstream_status_code
attempt
```

Why they help:

- better postmortems
- stronger cross-check with request payload
- easier operator review

## 7. What is not acceptable as success

The following are **not** PASS-worthy success shapes:

- `DONE` without `external_order_id`
- `DONE` without `execution_mode=testnet`
- `DONE` without `host_label`
- `DONE` with only stub-local fields
- `DONE` that cannot be tied back to `source` and `created_by`
- `DONE` that omits `idempotency_key`

These outcomes are too weak for canonical real external acceptance.

## 8. Relationship to event evidence

If success is real and accepted, review should also see compatible event evidence:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_ACCEPTED
ACTION_OK
MARK_DONE
```

The success shape does not replace the event chain.
Both must agree.

## 9. Relationship to negative evidence

Even when success shape is present, review must still confirm absence of contradiction:

- no `TESTNET_EXECUTOR_STUB` used as acceptance proof
- no live-host contamination
- no failure-family overwrite

The shape alone is not enough if the surrounding evidence disagrees.

## 10. Review questions this shape must answer

At `/commands/[id]`, a reviewer should be able to answer:

- was this the canonical `ORDER + execution_mode=testnet` path?
- which venue profile accepted it?
- what real upstream identifier proves acceptance?
- what normalized status was returned?
- who initiated it?
- what replay key ties this result to the intended command?

If any answer is unavailable, the success shape is incomplete.

## 11. Field integrity rules

The normalized success shape must not:

- leak secrets
- include API keys
- include request signatures
- include raw auth headers
- depend on raw upstream payload dumps to be understandable

The goal is:

```text
reviewable, stable, non-secret acceptance evidence
```

## 12. Relationship to adjacent docs

This rule aligns with:

- [docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md)
- [docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md)
- [docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md)
- [docs/REAL_TESTNET_OPEN_QUESTIONS_REGISTER_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPEN_QUESTIONS_REGISTER_V1.md)

It resolves Q-005 at the success-shape level.

## 13. What not to do

- Do not accept `DONE` with vague payload.
- Do not treat event evidence alone as enough if result shape is weak.
- Do not hide missing `external_order_id` behind generic “accepted”.
- Do not let stub-like shapes pass as real external success.
- Do not introduce live-trading semantics into this shape.

## 14. Recommended next bounded round

After this rule, the natural next round is:

```text
Real Testnet Failure Shape Rule V1
```

Scope:

```text
docs-only
resolve which normalized fields are mandatory for a FAIL-worthy real upstream failure result
no real key
no live trading
```

## 15. Acceptance for this rule

```text
PASS-worthy real success field set fixed: PASS
external_order_id required: PASS
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

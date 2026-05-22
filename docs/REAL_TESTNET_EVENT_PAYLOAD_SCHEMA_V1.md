# Real testnet event payload schema V1

**Status:** event-payload schema only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Security lead, interim).

**Date:** 2026-05-22

**Scope:** define the non-secret payload fields that must accompany future canonical real testnet executor events:

```text
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_ACCEPTED
TESTNET_EXECUTOR_REJECTED
```

Canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement new events. It fixes the review-facing event payload contract.

## 1. Decision

The canonical real testnet event payload schema applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be inferred from:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
TESTNET_EXECUTOR_STUB
```

The schema includes only non-secret review-safe fields.

## 2. Objective

The schema exists to answer one practical problem:

```text
when an operator sees TESTNET_EXECUTOR_REQUESTED / ACCEPTED / REJECTED,
what minimum fields must exist
so the event is actually useful for review and incident triage?
```

Without a fixed payload schema, the event names alone are too thin for reliable review.

## 3. Design rules

The event payload schema must follow these rules:

- fields must be non-secret
- fields must help distinguish attempted vs accepted vs rejected
- fields must help tie event evidence back to command review
- fields must not leak API keys, signatures, headers, or raw secrets
- fields should be stable enough for future automation and human review

## 4. Common required fields

These fields should appear on all three canonical real testnet executor events:

```text
command_id
attempt
execution_mode
market
symbol
side
order_type
source
created_by
idempotency_key_hash
host_label
event_ts
```

Notes:

- `execution_mode` must be `testnet`
- `idempotency_key_hash` is preferred over raw key when event payload is persisted broadly
- `host_label` should be the review-safe label derived from the named venue profile
- `event_ts` is the normalized event timestamp, not necessarily the raw upstream timestamp

## 5. Field meanings

| Field | Meaning | Secret risk |
|---|---|---|
| `command_id` | persisted command identifier | none |
| `attempt` | command attempt number | none |
| `execution_mode` | should be `testnet` | none |
| `market` | canonical market label | none |
| `symbol` | trading symbol | none |
| `side` | BUY/SELL | none |
| `order_type` | market/limit etc. | none |
| `source` | origin of command | none |
| `created_by` | operator/system initiator label | low, accepted |
| `idempotency_key_hash` | review-safe digest of idempotency key | low, preferred |
| `host_label` | named venue host label, not raw secret | none |
| `event_ts` | event emission timestamp | none |

## 6. TESTNET_EXECUTOR_REQUESTED payload

`TESTNET_EXECUTOR_REQUESTED` must mean:

```text
the canonical boundary passed local gates
and is about to attempt a real external request
```

Required fields:

```text
command_id
attempt
execution_mode
market
symbol
side
order_type
source
created_by
idempotency_key_hash
host_label
timeout_policy_label
event_ts
```

Recommended optional fields:

```text
notional
stop_price
venue_request_mode
```

Why `timeout_policy_label` matters:

- helps reviewers interpret later timeout failures
- proves which timeout profile was active

## 7. TESTNET_EXECUTOR_ACCEPTED payload

`TESTNET_EXECUTOR_ACCEPTED` must mean:

```text
the real upstream accepted the request enough
to return acceptance evidence
```

Required fields:

```text
command_id
attempt
execution_mode
market
symbol
side
order_type
source
created_by
idempotency_key_hash
host_label
external_order_id
external_status
event_ts
```

Recommended optional fields:

```text
venue_order_type
accepted_ts
upstream_status_code
```

Why `external_order_id` is required:

- without it, `ACCEPTED` is too weak for review
- it is one of the core acceptance proofs for real external contact

## 8. TESTNET_EXECUTOR_REJECTED payload

`TESTNET_EXECUTOR_REJECTED` must mean:

```text
the boundary attempted real external execution
but did not reach accepted outcome
```

Required fields:

```text
command_id
attempt
execution_mode
market
symbol
side
order_type
source
created_by
idempotency_key_hash
host_label
failure_family
failure_reason
event_ts
```

Recommended optional fields:

```text
upstream_status_code
upstream_error_class
timeout_stage
network_stage
```

Why `failure_family` is required:

- the event must already point into the approved taxonomy
- otherwise operators still have to guess what kind of rejection occurred

## 9. Field-specific rules

### `idempotency_key_hash`

Rule:

```text
store a review-safe digest, not the raw idempotency key, when broad persistence is possible
```

Purpose:

- tie retries/replays together
- reduce leakage of raw operational keys

### `host_label`

Rule:

```text
store the named venue host label,
not only the raw base URL string
```

Purpose:

- helps reviewers confirm venue profile selection
- stays aligned with host-safety rule

### `failure_reason`

Rule:

```text
must be human-comprehensible
but must not contain secrets, signatures, or raw credential material
```

### `upstream_status_code`

Rule:

```text
allowed when non-secret and meaningful,
not required for all failures,
but strongly recommended when upstream responded
```

## 10. Explicitly forbidden payload fields

These fields must not appear in persisted review-facing event payloads:

- API key
- API secret
- request signature
- raw authorization header
- raw cookie
- full raw upstream request body if it may contain secrets
- full raw upstream response body if it may contain secrets

If debugging needs them transiently, they must not become part of the normal review contract.

## 11. Review meaning by event

When operators see these events, they should be able to infer:

### `TESTNET_EXECUTOR_REQUESTED`

```text
local gates passed
host safety passed
kill switch passed
real external attempt is being made
```

### `TESTNET_EXECUTOR_ACCEPTED`

```text
real upstream accepted
an external order identifier exists
canonical success path is plausible
```

### `TESTNET_EXECUTOR_REJECTED`

```text
real external attempt happened
it did not succeed
taxonomy should explain why
```

## 12. Relationship to taxonomy and matrix

This schema must align with:

- [docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md)
- [docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md)
- [docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md)
- [docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md)

It does not replace them. It gives concrete payload expectations for their review logic.

## 13. What not to do

- Do not emit event names with empty or vague payloads.
- Do not include secrets for convenience.
- Do not emit `TESTNET_EXECUTOR_ACCEPTED` without `external_order_id`.
- Do not emit `TESTNET_EXECUTOR_REJECTED` without `failure_family`.
- Do not reuse stub payload semantics for real executor events.

## 14. Recommended next bounded round

After this schema, the natural next round is:

```text
Real Testnet Success Shape Rule V1
```

Scope:

```text
docs-only
resolve which normalized fields are mandatory for a PASS-worthy real upstream success result
no real key
no live trading
```

## 15. Acceptance for this schema

```text
canonical payload schema fixed for REQUESTED / ACCEPTED / REJECTED: PASS
common required fields stated: PASS
ACCEPTED requires external_order_id: PASS
REJECTED requires failure_family: PASS
secret-bearing fields explicitly forbidden: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

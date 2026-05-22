# Real testnet open questions register V1

**Status:** open-question register only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** collect the remaining unanswered questions that still block the future canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This register does not resolve the questions. It makes them explicit so implementation does not drift into unstated assumptions.

## 1. Decision

This register applies only to:

```text
ORDER + execution_mode=testnet
```

It does not treat these as acceptable substitutes:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
TESTNET_EXECUTOR_STUB
live trading
```

## 2. Why this register exists

The document stack is now mature enough that the remaining blockers are less about missing narrative and more about unanswered decisions.

This register exists to answer one question:

```text
what still must be decided before real testnet implementation can be safely attempted?
```

## 3. Open questions

### Q-001. What exact market label becomes canonical for the first real testnet venue?

Current state:

```text
docs use examples like binance_testnet
```

Open question:

```text
is the first canonical market string exactly `binance_testnet`,
or do we need a more generic abstraction from day one?
```

Why it matters:

- affects payload contract stability
- affects review vocabulary
- affects future multi-venue expansion

Blocked area:

```text
real executor implementation
result normalization
```

### Q-002. What exact upstream host safety rule will be enforced?

Current state:

```text
canonical TESTNET_EXCHANGE_BASE_URL is defined,
but exact hostname allowlist policy is not fixed
```

Open question:

```text
do we enforce a strict allowlist,
a suffix rule,
or an explicit named venue map?
```

Why it matters:

- determines how we prove “testnet-only”
- prevents accidental live host usage

Blocked area:

```text
base-url validation
credential wiring
```

### Q-003. What is the exact kill switch evidence source of truth at executor boundary?

Current state:

```text
docs require kill switch proof before signed HTTP
```

Open question:

```text
what exact runtime source counts as authoritative at boundary time:
redis state, env override, merged state, or another single source?
```

Why it matters:

- boundary proof must be auditable
- ambiguous source weakens refusal evidence

Blocked area:

```text
kill switch real-boundary implementation
operator review trust
```

### Q-004. What exact event payload should accompany TESTNET_EXECUTOR_REQUESTED and TESTNET_EXECUTOR_ACCEPTED?

Current state:

```text
event names are specified,
but event payload fields are not fully fixed
```

Open question:

```text
which non-secret fields must be attached:
host label, venue label, request mode, attempt, timeout class, idempotency key hash?
```

Why it matters:

- affects postmortem usefulness
- affects ability to distinguish attempted vs accepted cleanly

Blocked area:

```text
event schema
review evidence quality
```

### Q-005. What is the minimal accepted success shape from a real upstream response?

Current state:

```text
docs describe normalized result fields,
but do not yet fix which ones are mandatory vs optional
```

Open question:

```text
which fields are mandatory for PASS:
external_order_id, external_status, ts, venue_order_type echo, host label?
```

Why it matters:

- avoids fuzzy “DONE” acceptance
- fixes command detail review standard

Blocked area:

```text
result normalization
smoke acceptance
```

### Q-006. What is the minimal accepted failure shape from a real upstream response?

Current state:

```text
failure taxonomy is fixed,
but field-level normalized failure payload is not yet fully fixed
```

Open question:

```text
which fields are mandatory for FAIL review:
failure_family, reason, upstream_status_code, host label, timeout stage?
```

Why it matters:

- keeps failure taxonomy reviewable
- avoids vague failures after implementation

Blocked area:

```text
failure normalization
review checklist rigor
```

### Q-007. What timeout policy is canonical for the first real testnet attempt?

Current state:

```text
timeout failure family exists,
but timeout thresholds and retry posture are not fixed
```

Open question:

```text
do we allow zero retries,
single retry,
or no retry with explicit operator replay only?
```

Why it matters:

- affects idempotency risk
- affects meaning of `TESTNET_EXECUTOR_TIMEOUT`

Blocked area:

```text
executor behavior
operator expectations
```

### Q-008. How is idempotency enforced across retries or replays?

Current state:

```text
idempotency_key is required,
but replay semantics are not fully specified for real external attempts
```

Open question:

```text
does the executor persist outbound attempt fingerprints,
or is idempotency delegated entirely to upstream plus command state?
```

Why it matters:

- prevents duplicate real testnet orders
- affects timeout/retry design

Blocked area:

```text
executor retry policy
smoke replay safety
```

### Q-009. What exact credential handoff model is allowed?

Current state:

```text
secrets custody plan exists,
canonical env names exist,
but runtime injection model is not fixed
```

Open question:

```text
will credentials arrive via process env only,
secret manager sync,
or an adapter layer that materializes env at runtime?
```

Why it matters:

- determines audit surface
- determines failure mode for missing credentials

Blocked area:

```text
deployment boundary
credential failure handling
```

### Q-010. What exact proof is required to declare legacy QUOTE path non-operational?

Current state:

```text
legacy path is downgraded by docs,
but practical retirement proof is not yet fixed
```

Open question:

```text
do we require code removal,
feature flag isolation,
or explicit test evidence that canonical review never uses it?
```

Why it matters:

- avoids dual-path confusion
- protects canonical review process

Blocked area:

```text
implementation cleanup
operator trust
```

### Q-011. What exact operator evidence is sufficient for a blocked review vs failed review?

Current state:

```text
runbook distinguishes PASS / FAIL / BLOCKED,
but the edge between BLOCKED and FAIL is not yet fully enumerated
```

Open question:

```text
which cases are BLOCKED:
missing page access,
missing event payload,
missing host label,
ambiguous state?
```

Why it matters:

- prevents inconsistent human review outcomes
- affects release governance

Blocked area:

```text
operator procedure
incident escalation clarity
```

### Q-012. What exact first implementation slice is safest after docs-only readiness work?

Current state:

```text
the docs stack is now broad,
but the first code slice after this is not yet chosen
```

Open question:

```text
should the next implementation be:
host/base-url validation,
credential presence gate,
event payload shaping,
or executor adapter shell?
```

Why it matters:

- determines the smallest safe code-entry point
- avoids over-jumping into full external execution

Blocked area:

```text
next engineering slice selection
```

## 4. Prioritization

Recommended resolution order:

1. `Q-002` host safety rule
2. `Q-003` kill switch source of truth
3. `Q-009` credential handoff model
4. `Q-004` event payload schema
5. `Q-005` success shape
6. `Q-006` failure shape
7. `Q-008` idempotency enforcement
8. `Q-007` timeout/retry policy
9. `Q-010` legacy path retirement proof
10. `Q-011` BLOCKED vs FAIL boundary
11. `Q-001` canonical market label
12. `Q-012` first implementation slice

## 5. What this register does not mean

This register does **not** mean:

- real testnet is approved
- any key should be added
- external API calls are allowed now
- live trading is closer than the docs say

It only means the unresolved decision surface is now visible.

## 6. Recommended next bounded round

After this register, the natural next round is:

```text
Real Testnet Host Safety Rule V1
```

Scope:

```text
docs-only
resolve Q-002 by defining the exact host safety / allowlist rule
no real key
no live trading
```

## 7. Acceptance for this register

```text
remaining real-testnet blockers collected: PASS
questions tied to canonical ORDER + execution_mode=testnet path: PASS
priority order stated: PASS
legacy and stub paths excluded as substitutes: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

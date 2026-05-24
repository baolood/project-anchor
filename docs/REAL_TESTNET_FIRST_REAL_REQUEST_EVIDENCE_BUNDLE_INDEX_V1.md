# Real testnet first real request evidence bundle index V1

**Status:** evidence-bundle index only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-24**

**Scope:** collect signoff, runtime-window, execution record, review closeout, and review-artifact links into one bounded first-request evidence bundle index for the canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This bundle does not authorize the first real request.
It provides one concise evidence-reading order for the moment when that request is finally attempted.

## 1. Decision

The first real request now has enough adjacent docs that future review would become slow and error-prone without a compact evidence bundle.

This index is meant to answer:

```text
once the first real request happens,
what exact evidence stack should be read,
in what order,
to reach a bounded final conclusion?
```

## 2. Recommended reading order

Read the first-request evidence in this order.

### A. Pre-send posture

1. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md)

Purpose:

```text
who approved,
what posture was intended,
and what pre-send commitments were made
```

### B. Runtime-window behavior

2. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md)

Purpose:

```text
what happened inside the bounded runtime window itself
```

### C. Canonical command evidence

3. `/ops -> /commands -> /commands/[id]`
4. [docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md)

Purpose:

```text
what final state, event family, normalized family,
and external request status actually appeared
```

### D. Final review wrapper

5. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_REVIEW_CLOSEOUT_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_REVIEW_CLOSEOUT_V1.md)

Purpose:

```text
how to unify signoff, runtime-window facts,
command evidence, and final verdict
```

### E. Durable artifact location

6. [docs/reviews/real_testnet/README.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/README.md)
7. [docs/reviews/real_testnet/INDEX.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/INDEX.md)

Purpose:

```text
where the durable final review artifact belongs
and how its label should be chosen
```

## 3. Questions this bundle should answer

After reading the bundle, a reviewer should be able to answer:

1. Was the request actually attempted or correctly blocked?
2. Was the runtime window bounded and explicitly controlled?
3. What command evidence appeared?
4. Did the event family and normalized family make sense?
5. Was retreat required?
6. Is a second real request still blocked or allowed?

If those questions remain unanswered, the bundle is incomplete.

## 4. What this bundle does not replace

This evidence bundle does not replace:

- the wider real-testnet readiness stack
- runtime verification materials
- dry activation rehearsal materials
- ingress and host-boundary planning materials

Those remain upstream.
This bundle exists only for the first actual request review moment.

## 5. Expected closeout labels

The bundle should resolve to one of:

### `PASS`

Meaning:

- signoff posture, runtime-window facts, and command evidence all align
- the first request is reviewable and bounded

### `BLOCKED`

Meaning:

- the request was intentionally not sent
- or the review correctly stopped before an unsupported conclusion

### `FAIL`

Meaning:

- the request crossed into contradictory or non-reviewable behavior
- or the bounded process broke down in a way that prevents safe acceptance

## 6. Stable status statement

At this point the correct evidence-bundle summary is:

```text
the first real request now has a bounded evidence reading order
signoff, runtime-window facts, command evidence, and final closeout can be reviewed as one stack
the actual request is still gated, but the evidence path is becoming operationally ready
live trading: NO-GO
```

## 7. Minimal next bounded round

After this bundle, the next natural bounded round is:

```text
Real Testnet First Real Request Bundle Closeout V1
```

Scope:

```text
docs-only
record that the first-request evidence stack is now complete enough
for an eventual bounded attempt, and identify what still blocks the actual send
```

# Real Testnet first controlled send evidence bundle index V1

**Status:** evidence-bundle index only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

**Scope:** collect signoff, opened-window facts, runtime-verification record, attempt record, final review closeout, and review-artifact links into one bounded first-controlled-send evidence bundle index for the canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This bundle does not authorize the first controlled send.
It provides one concise evidence-reading order for the moment when that bounded send is finally attempted and reviewed.

## 1. Decision

The first controlled send now has enough adjacent docs that future review would become slow and error-prone without one compact evidence bundle.

This index is meant to answer:

```text
once the first controlled send happens,
what exact evidence stack should be read,
in what order,
to reach one bounded final reviewed conclusion?
```

## 2. Recommended reading order

Read the first-controlled-send evidence in this order.

### A. Pre-send posture

1. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md)

Purpose:

```text
who approved,
what posture was intended,
and what pre-send commitments were made
```

### B. Opened-window transition

2. [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_V1.md)

Purpose:

```text
when the candidate window truly opened
and what posture existed at that moment
```

### C. Runtime verification

3. [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_V1.md)

Purpose:

```text
what bounded runtime facts were explicitly re-confirmed
immediately before the first controlled send
```

### D. Attempt moment

4. [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_ATTEMPT_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_ATTEMPT_RECORD_V1.md)

Purpose:

```text
what happened at the exact first controlled send moment itself
```

### E. Canonical command evidence

5. `/ops -> /commands -> /commands/[id]`
6. [docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md)

Purpose:

```text
what final state, event family, normalized family,
and external request status actually appeared
```

### F. Final review wrapper

7. [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLOSEOUT_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLOSEOUT_V1.md)

Purpose:

```text
how to unify signoff, opened-window facts,
runtime verification, attempt evidence,
command evidence, and final verdict
```

### G. Durable artifact location

8. [docs/reviews/real_testnet/README.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/README.md)
9. [docs/reviews/real_testnet/INDEX.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/INDEX.md)

Purpose:

```text
where the durable final review artifact belongs
and how its label should be chosen
```

## 3. Questions this bundle should answer

After reading the bundle, a reviewer should be able to answer:

1. Was the window actually opened under the expected posture?
2. Was the runtime-verification step actually completed under bounded facts?
3. Was exactly one canonical controlled send attempted, or correctly blocked?
4. What command evidence appeared?
5. Did the event family and normalized family make sense?
6. Was retreat required?
7. Is a second controlled send still blocked or allowed?

If those questions remain unanswered, the bundle is incomplete.

## 4. What this bundle does not replace

This evidence bundle does not replace:

- the wider real-testnet readiness stack
- cloud host access and runtime-boundary materials
- dry activation rehearsal materials
- ingress and host-boundary planning materials

Those remain upstream.
This bundle exists only for the first actual controlled-send review moment.

## 5. Expected closeout labels

The bundle should resolve to one of:

### `PASS`

Meaning:

- signoff posture, opened-window facts, runtime verification, attempted-send facts, and command evidence all align
- the first controlled send is reviewable and bounded

### `BLOCKED`

Meaning:

- the controlled send was intentionally not completed
- or the review correctly stopped before an unsupported conclusion

### `FAIL`

Meaning:

- the controlled send crossed into contradictory or non-reviewable behavior
- or the bounded process broke down in a way that prevents safe acceptance

## 6. Stable status statement

At this point the correct evidence-bundle summary is:

```text
the first controlled send now has a bounded evidence reading order
signoff, opened-window facts, runtime verification, attempt evidence,
command evidence, and final closeout can be reviewed as one stack
the actual send is still gated, but the evidence path is now operationally ready
live trading: NO-GO
```

## 7. Minimal next bounded round

After this bundle, the next natural bounded round is:

```text
Real Testnet First Controlled Send Bundle Closeout V1
```

Scope:

```text
docs-only
record that the first-controlled-send evidence stack is now complete enough
for an eventual bounded attempt and final reviewed conclusion,
and identify what still blocks the actual live runtime proof
```

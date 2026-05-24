# Real Testnet first real request scheduling gate bundle V1

**Status:** scheduling-gate bundle only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** collect the scheduling packet, scheduling decision gate, and upstream first-request prerequisites into one final pre-window review bundle for the canonical first real external testnet request:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This bundle does not open the runtime window by itself.
It creates one bounded reading order for the last review moment before the first real request may actually be attempted.

## 1. Decision

At this point the project has enough first-request preparation material that the last pre-window review should no longer depend on scattered docs or chat memory.

This bundle exists to answer:

```text
if we are about to decide whether the first real request window may open,
what exact packet and gate material should the reviewer read,
and in what order,
to reach one bounded go/no-go conclusion
```

## 2. Recommended reading order

Read the final pre-window review stack in this order.

### A. Attempt prerequisites

1. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_CONTROLLED_ATTEMPT_PREREQ_CHECK_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_CONTROLLED_ATTEMPT_PREREQ_CHECK_V1.md)

Purpose:

```text
verify the final explicit prerequisites that must all be true
before the first real request may even be scheduled
```

### B. Scheduling packet

2. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_PACKET_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_PACKET_V1.md)

Purpose:

```text
see the exact bounded packet that describes
the host, posture, review surfaces, planned command,
and linked evidence for the first attempt
```

### C. Scheduling decision gate

3. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_DECISION_GATE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_DECISION_GATE_V1.md)

Purpose:

```text
apply the final go/no-go rule
for whether the completed scheduling packet is strong enough
to let the runtime window open
```

### D. Runtime-window posture

4. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md)
5. [docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md)
6. [docs/CLOUD_HOST_ACCESS_RETREAT_DRILL_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/CLOUD_HOST_ACCESS_RETREAT_DRILL_SPEC_V1.md)

Purpose:

```text
confirm the runtime window can be opened, verified, and retreated from
without improvisation
```

### E. Downstream evidence path

7. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_EVIDENCE_BUNDLE_INDEX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EVIDENCE_BUNDLE_INDEX_V1.md)
8. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_REVIEW_CLOSEOUT_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_REVIEW_CLOSEOUT_V1.md)

Purpose:

```text
confirm that if the window opens,
the resulting evidence already has a bounded review and closeout path
```

## 3. Questions this bundle must answer

After reading this bundle, the reviewer should be able to answer all of these:

1. Is the canonical path still `ORDER + execution_mode=testnet`?
2. Are the final prerequisites explicit rather than implied?
3. Is the exact planned command bounded enough for one first attempt?
4. Is the runtime posture explicit enough to distinguish `mock`, `real-but-disabled`, and `real-enabled-for-bounded-window`?
5. Is the retreat posture immediate and credible?
6. Are the review surfaces reachable enough that sendability does not outrun reviewability?
7. If the gate says `PASS`, do we know exactly what will happen next?
8. If the gate says `BLOCKED`, do we know exactly why the window must stay closed?

If the bundle cannot answer these, it is incomplete.

## 4. What this bundle is not

This bundle is not:

- the actual runtime-window execution record
- the actual signoff artifact for a real attempt
- the first-request review closeout itself
- proof that a real request has already happened

It is the final review entrypoint before that operational proof exists.

## 5. Expected output of the bundle review

The bundle review should end in one of these:

### `PASS - WINDOW MAY OPEN`

Meaning:

- the packet is complete
- the decision gate is satisfied
- runtime posture and retreat posture are credible
- the project may open one bounded first-request window

### `BLOCKED - WINDOW MUST STAY CLOSED`

Meaning:

- a prerequisite is still weak or missing
- the packet is incomplete or not credible
- the decision gate correctly refuses to open the window

### `FAIL - PRE-WINDOW PROCESS BREACH`

Meaning:

- the project tries to open the window without respecting the packet/gate structure
- or the bundle is later shown to misrepresent actual posture

## 6. Stable status statement

At this point the correct bundle summary is:

```text
the project now has a final pre-window review bundle
that joins prerequisites, scheduling packet, decision gate,
runtime posture materials, and downstream evidence path
the first real request remains gated,
but the last review entrypoint is now bounded and coherent
```

## 7. Minimal next bounded round

After this bundle, the next natural bounded round is:

```text
Real Testnet First Real Request Gate Bundle Closeout V1
```

Scope:

```text
docs-only
record that the final pre-window review bundle is now complete,
and state exactly what still separates readiness from the actual first controlled send
```

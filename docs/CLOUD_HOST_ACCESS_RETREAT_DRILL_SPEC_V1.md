# Cloud host access retreat drill spec V1

**Status:** retreat drill spec only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the smallest operator drill for retreating from a bounded real-attempt cloud-host posture back to `mock` or fail-closed posture after a first-real-request anomaly, ambiguity, or unexpected evidence signal.

This drill does not authorize a real request.
It standardizes what “retreat immediately” must mean in practice before that first request is ever attempted.

## 1. Decision

If the first guarded real testnet request shows any anomaly, the cloud host response must not depend on improvisation.

The operator should be able to perform one small retreat drill that proves all of these:

- further real attempts can be stopped immediately
- runtime posture can return to `mock` or fail-closed
- evidence can be preserved before any second attempt
- review can continue without losing what happened

If this drill cannot be described clearly, the first real request should remain:

```text
BLOCKED
```

## 2. What this drill is trying to prove

This drill exists to answer one narrow question:

```text
after a suspicious or failed first real-attempt signal,
can the operator stop, retreat, preserve evidence, and avoid a second uncontrolled try?
```

This drill is not:

- a live rollback exercise
- a deploy rollback procedure
- a retry strategy
- a throughput test

It is a smallest-possible retreat exercise for the current guarded cloud-host stage.

## 3. Trigger conditions

The retreat drill should be considered applicable whenever any of these happen:

- contradictory runtime mode evidence
- missing or malformed `TESTNET_EXECUTOR_REQUESTED`
- missing expected `TESTNET_EXECUTOR_ACCEPTED` or `TESTNET_EXECUTOR_REJECTED`
- unexpected failure family
- host label / configured origin mismatch
- any sign that evidence is not cleanly reviewable
- operator uncertainty about whether a second real attempt is safe

If the operator says “something looks off, but maybe one more quick try,” that is already a retreat-triggering signal.

## 4. Smallest retreat objective

The smallest acceptable retreat outcome is:

```text
no further real-attempt commands
runtime posture no longer able to continue real mode casually
first-attempt evidence preserved
review path remains intact
```

This means the drill is successful only if the system becomes more conservative, not merely “paused mentally.”

## 5. Required retreat actions

When the drill is invoked, the operator should conceptually perform these actions in order:

1. stop any plan for a second real request
2. force runtime posture back to `mock` or fail-closed
3. preserve the exact command/evidence path for the first anomaly
4. route review back through `/ops -> /commands -> /commands/[id]`
5. open or complete the signoff / review artifact before any follow-up decision

The key rule is:

```text
retreat first
review second
consider any next action only after review
```

## 6. Required runtime retreat posture

After retreat, the operator should be able to state plainly that one of these is true:

- `TESTNET_EXECUTOR_MODE=mock`
- or real mode is no longer usable because the runtime is back to fail-closed posture

Retreat should never leave the system in an ambiguous “maybe real is still enabled” state.

At minimum, retreat should restore a posture where:

- accidental second real request is materially harder
- preflight refusal families are still available
- `TESTNET_REAL_WIRE_DISABLED` remains reachable when expected

## 7. Required evidence preservation

The retreat drill is incomplete unless the operator can preserve enough evidence to answer:

- what command was involved
- whether the path reached external-attempt boundary
- what final command state resulted
- which normalized family appeared
- why retreat was chosen

Minimum preserved evidence should still include:

- `command_id` if one exists
- runtime mode posture used during the attempt
- host label / configured origin identity
- `/commands/[id]` review output
- signoff/review artifact notes explaining the anomaly

## 8. Required “do not do this” rules

During retreat, the operator must not:

- perform a quick second real attempt
- patch runtime posture mid-incident without recording it
- treat terminal output alone as sufficient closure
- overwrite or hide the first anomaly evidence
- reclassify an unclear result as `PASS`

If any of those occur, the drill should be treated as failed.

## 9. Minimum rehearsal standard

Before the actual first real request, the operator should at least be able to verbally or procedurally walk through:

- where the retreat decision is made
- how runtime posture is changed back
- where review evidence is checked
- where the signoff or artifact is completed
- who is allowed to authorize any subsequent attempt

This does not require a full fire drill with real keys.
It does require more than “we’ll figure it out if something goes wrong.”

## 10. Minimum retreat result labels

Use these interpretation labels for the drill itself:

### `PASS`

Only if:

- retreat path is unambiguous
- runtime can clearly return to `mock` or fail-closed
- evidence preservation path is clear
- second-attempt suppression is explicit

### `BLOCKED`

Use if:

- retreat depends on memory or improvisation
- runtime posture after retreat would still be ambiguous
- evidence preservation is unclear
- reviewer ownership after retreat is unclear

### `FAIL`

Use if:

- the presumed retreat posture could still allow casual second real attempts
- anomaly evidence would be lost or contradicted
- operator cannot explain who stops, who reviews, and when a second attempt is forbidden

## 11. Stable status statement

At this point the correct retreat summary is:

```text
first real request remains guarded
retreat must be immediate, conservative, and review-preserving
no quick second real attempt is acceptable
domain: still not required
live trading: NO-GO
```

## 12. Minimal next bounded round

After this drill spec, the next natural host-related bounded round is:

```text
Cloud Host Runtime Verification Checklist V1
```

Scope:

```text
docs-only
compress the specific runtime values, mode checks, and host signals
an operator should verify during the request window itself
```

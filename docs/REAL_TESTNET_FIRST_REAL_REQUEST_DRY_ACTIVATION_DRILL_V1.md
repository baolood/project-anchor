# Real testnet first real request dry activation drill V1

**Status:** dry activation drill only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-24**

**Scope:** define a no-external-call rehearsal for opening the bounded first-real-request runtime window, confirming roles and posture, exercising stop/retreat readiness, and closing the window cleanly without sending a real request.

This drill does not authorize or send a real request.
It exists to rehearse the human/runtime choreography before that higher-risk step is attempted.

## 1. Decision

Before the first real testnet request, the team should be able to rehearse the runtime window without crossing into actual external-attempt evidence.

The dry activation drill should prove:

- the window can be opened deliberately
- roles are explicit
- runtime posture can be named
- stop and retreat logic are ready
- the window can be closed cleanly without “just trying the request”

If this cannot be done cleanly, the real request should remain:

```text
BLOCKED
```

## 2. Objective

The drill exists to answer one narrow question:

```text
can we rehearse the first-real-request control flow
without sending a real request
and still learn whether the people, posture, and stop logic are ready?
```

This is not:

- a mock executor feature test
- a load test
- a deploy test
- an excuse to widen ingress

It is a bounded rehearsal of window mechanics.

## 3. What the drill should include

The dry activation drill should include all of these:

- name the operator
- name the reviewer
- identify the host and intended revision
- state the current runtime posture
- confirm review surfaces are reachable
- confirm retreat path is ready
- open the window explicitly
- pause before the actual request step
- close the window explicitly as rehearsal only

This means the drill validates sequencing and readiness, not transport behavior.

## 4. What the drill must not include

The dry activation drill must not:

- send a real testnet request
- enable a real request just to “see if it works”
- create external-attempt evidence intentionally
- perform ingress/deploy/config changes as part of the same rehearsal
- turn into a broader debugging session

If the drill starts drifting into any of those, stop and mark it `FAIL` or `BLOCKED`.

## 5. Recommended phases

### Phase 1. Pre-open identity check

Confirm:

- host identity
- revision/runtime identity
- operator identity
- reviewer identity

If these are fuzzy, stop immediately.

### Phase 2. Runtime posture naming

State plainly:

- executor mode value
- whether real wire is disabled or not
- whether current posture is:
  - `mock`
  - `real-but-disabled`
  - `invalid / blocked`

If posture cannot be named, do not continue.

### Phase 3. Review-path confirmation

Confirm the fixed path is still usable:

```text
/ops
-> /commands
-> /commands/[id]
```

For this drill, command detail may be a previously known reviewable command or a placeholder review path check.
The point is to confirm the review route still exists, not to prove a new command.

### Phase 4. Stop/retreat rehearsal

Verbally or procedurally confirm:

- what would trigger a stop
- who is allowed to call the stop
- how the posture would retreat to `mock` or fail-closed
- that no second attempt would happen before review

If the participants cannot explain this cleanly, the drill has already found a blocker.

### Phase 5. Explicit close

Close the window with a clear statement:

```text
no real request was sent
window closed as rehearsal
next action remains gated
```

This prevents the drill from turning into an undefined halfway state.

## 6. Minimum drill checklist

Use this short checklist:

```text
drill_id:
timestamp_open:
operator:
reviewer:
witness:

host_identity_confirmed: yes/no
revision_confirmed: yes/no
runtime_posture_named: yes/no
review_path_confirmed: yes/no
stop_logic_confirmed: yes/no
retreat_path_confirmed: yes/no

window_opened: yes/no
real_request_sent: yes/no
window_closed_cleanly: yes/no

verdict: PASS/BLOCKED/FAIL
notes:
```

## 7. PASS criteria

This drill is `PASS` only if:

- roles are explicit
- runtime posture is named clearly
- review path is confirmed
- retreat logic is confirmed
- no real request is sent
- the window is explicitly opened and explicitly closed

## 8. BLOCKED criteria

This drill is `BLOCKED` if:

- identities are unclear
- runtime posture cannot be named clearly
- review surfaces are uncertain
- retreat logic is unclear
- the team cannot keep the rehearsal bounded away from a real attempt

This is a healthy finding.

## 9. FAIL criteria

This drill is `FAIL` if:

- someone sends a real request during the rehearsal
- the drill is used to justify ingress or deploy mutation
- stop/retreat logic is contradicted in practice
- the window is opened but not cleanly closed

## 10. Stable status statement

At this point the correct dry-activation summary is:

```text
the team should rehearse opening and closing the first-real-request window before using it
no-external-call rehearsal is part of safety, not delay
real request remains gated until the rehearsal is clean
live trading: NO-GO
```

## 11. Minimal next bounded round

After this drill, the next natural bounded round is:

```text
Real Testnet First Real Request Execution Record V1
```

Scope:

```text
docs-only
define the exact runtime-window execution record that should be filled
when the first real request is actually attempted
```

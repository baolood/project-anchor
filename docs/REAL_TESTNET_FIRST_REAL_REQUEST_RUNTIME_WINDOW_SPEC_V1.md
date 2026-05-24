# Real testnet first real request runtime window spec V1

**Status:** runtime-window spec only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-24**

**Scope:** define the exact bounded runtime window assumptions, roles, sequencing, and stop conditions for the actual first real external testnet request on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize the first real request by itself.
It defines what the request window should look like once the project is ready to attempt it.

## 1. Decision

The first real testnet request should happen only inside a deliberately short, role-explicit, review-first runtime window.

That window should be treated as:

```text
bounded
single-purpose
reviewable
easy to stop
```

It must not be treated as:

```text
open-ended testing time
a broader experimentation session
an ingress or deploy window
```

## 2. Objective

The runtime window exists to answer one narrow question:

```text
under a fixed host boundary and explicit runtime posture,
can one canonical real testnet request be attempted,
classified,
and either accepted into review or immediately retreated from?
```

It is not meant to prove throughput, concurrency, or repeated reliability in one sitting.

## 3. Fixed window assumptions

The runtime window assumes all of these remain true:

- canonical path is still `ORDER + execution_mode=testnet`
- live trading remains `NO-GO`
- ingress posture remains frozen
- domain/public-ingress work remains out of scope
- retreat to `mock` or fail-closed posture remains immediately possible
- the operator review path remains:

```text
/ops
-> /commands
-> /commands/[id]
```

If any assumption changes mid-window, the window should stop.

## 4. Required roles

The runtime window should not be role-ambiguous.

At minimum, these roles should be explicit:

### A. Operator

Responsible for:

- runtime posture confirmation
- command submission or supervised execution step
- host-side observation
- immediate retreat action if required

### B. Reviewer

Responsible for:

- confirming readiness assumptions
- validating evidence through `/commands/[id]`
- classifying outcome as `PASS`, `BLOCKED`, or `FAIL`
- blocking any second attempt when evidence is unclear

### C. Optional witness / secondary reviewer

Useful but not mandatory.
If present, this role exists to reduce ambiguity, not to add bureaucracy.

## 5. Window phases

The runtime window should be treated as five phases.

### Phase 1. Pre-open confirmation

Confirm:

- host identity
- revision/runtime identity
- mode/toggle posture
- canonical env and host safety posture
- review surfaces reachable
- retreat path ready

If Phase 1 is incomplete, do not open the window.

### Phase 2. Bounded open

The window is explicitly “open” only after:

- operator says runtime posture is explicit
- reviewer says stop conditions are clear
- both agree no ingress/deploy changes are being mixed into the window

This is a control boundary, not just a mood.

### Phase 3. Single request attempt

Inside the window:

- one canonical request only
- one unique idempotency key
- one bounded operator action
- no batch
- no retry
- no concurrent “let’s also test this” side work

If a second command becomes tempting, that is already a signal to stop and review.

### Phase 4. Immediate evidence review

After the request:

- inspect `/ops`
- inspect `/commands`
- inspect `/commands/[id]`
- confirm final state
- confirm event family
- confirm normalized family
- confirm whether retreat is required

Do not close the window from terminal output alone.

### Phase 5. Close or retreat

Close only after:

- the result is explicitly classified
- reviewer notes are captured
- retreat decision is explicit

If evidence is unclear, do not “leave it open and come back later” as if nothing happened.
The window should end in either clear closeout or retreat.

## 6. Allowed actions inside the window

Allowed:

- runtime verification
- one bounded canonical request
- review through the fixed surfaces
- read-only log inspection
- explicit retreat to `mock` or fail-closed posture
- artifact/signoff completion

Not allowed:

- second real request before first request is fully classified
- ingress widening
- deploy/config mutation as part of the same experiment
- broad debugging detours
- mixing unrelated command or workflow experiments into the same window

## 7. Hard stop conditions

The runtime window must stop immediately if any of these occur:

- runtime posture becomes ambiguous
- host label or origin mismatch appears
- review surfaces become unavailable
- `TESTNET_EXECUTOR_REQUESTED` / `ACCEPTED` / `REJECTED` evidence is contradictory
- normalized family is unclear
- evidence preservation becomes uncertain
- any participant suggests “one quick retry” before review

If a hard stop triggers, the window transitions to retreat/review, not continued experimentation.

## 8. Minimum runtime window template

Use this short template:

```text
window_id:
timestamp_open:
operator:
reviewer:
witness:

host_identity_confirmed: yes/no
revision_confirmed: yes/no
runtime_posture_confirmed: yes/no
review_surfaces_confirmed: yes/no
retreat_ready: yes/no

window_opened: yes/no
single_request_attempted: yes/no
command_id:

final_state:
event_family:
normalized_family:
external_request_status:
retreat_required: yes/no

window_closed: yes/no
verdict: PASS/BLOCKED/FAIL
notes:
```

## 9. PASS criteria

This runtime window spec is `PASS` only if:

- the window is explicitly opened and closed
- roles are explicit
- only one bounded canonical request is attempted
- review happens immediately through the fixed path
- hard stop conditions remain effective
- retreat remains available
- no unrelated ingress/deploy/debug work is mixed in

## 10. BLOCKED criteria

This runtime window spec is `BLOCKED` if:

- runtime assumptions are unclear before opening
- roles are ambiguous
- review path is incomplete
- retreat path is not immediate
- the team cannot keep the request bounded to one canonical attempt

This is a healthy refusal, not lost progress.

## 11. Stable status statement

At this point the correct runtime-window summary is:

```text
the first real request should happen inside a short explicit runtime window
with named roles, one canonical attempt, immediate review, and immediate retreat if needed
domain and ingress work stay out of that window
live trading: NO-GO
```

## 12. Minimal next bounded round

After this spec, the next natural bounded round is:

```text
Real Testnet First Real Request Dry Activation Drill V1
```

Scope:

```text
docs-only
define a no-external-call rehearsal for opening the runtime window,
confirming roles and posture, and closing it cleanly without sending a real request
```

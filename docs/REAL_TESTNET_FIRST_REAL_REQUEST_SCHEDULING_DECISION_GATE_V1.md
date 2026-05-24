# Real Testnet first real request scheduling decision gate V1

**Status:** scheduling decision gate only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the exact final go/no-go rule for when a completed first-real-request scheduling packet may actually open the bounded runtime window for the first real external testnet request on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize the request by default.
It defines the last explicit decision gate between “packet complete” and “runtime window may open.”

## 1. Decision

A completed scheduling packet is necessary, but not sufficient, to open the first real request window.

The runtime window may open only if a reviewer can explicitly conclude:

```text
the packet is complete,
the canonical path is stable,
the runtime posture is explicit,
the retreat posture is immediate,
and opening the window will not mix first-send proof with unrelated runtime changes
```

If any one of those statements is weak, ambiguous, or contradicted, result is:

```text
BLOCKED - do not open the runtime window
```

## 2. Fixed applicability

This decision gate applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be used for:

- legacy `QUOTE + BINANCE_TESTNET`
- `TESTNET_EXECUTOR_STUB`
- mock-only runs
- live trading

## 3. What this gate is deciding

This gate decides one narrow thing:

```text
can the project move from prepared posture
to one bounded runtime window for one real testnet request
without exceeding the current review and retreat discipline
```

It does not decide:

- whether real testnet is fully mature
- whether a second request is allowed
- whether any public ingress/domain work should start
- whether live trading can ever be considered

## 4. Gate inputs

The reviewer must make this decision from a bounded set of inputs:

1. scheduling packet  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_PACKET_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_PACKET_V1.md)
2. controlled-attempt prereq check  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_CONTROLLED_ATTEMPT_PREREQ_CHECK_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_CONTROLLED_ATTEMPT_PREREQ_CHECK_V1.md)
3. runtime window spec  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md)
4. cloud host runtime verification checklist  
   [docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md)
5. cloud host retreat drill spec  
   [docs/CLOUD_HOST_ACCESS_RETREAT_DRILL_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/CLOUD_HOST_ACCESS_RETREAT_DRILL_SPEC_V1.md)

If the reviewer needs broader unstated context to make the decision, the packet is not truly complete.

## 5. Mandatory go conditions

The runtime window may open only if all of these are explicitly true:

### A. Path and posture

- canonical path is still `ORDER + execution_mode=testnet`
- legacy path is not being used as fallback or proof
- runtime posture is explicitly named
- `TESTNET_EXECUTOR_MODE` intent is explicit
- `TESTNET_EXECUTOR_REAL_ENABLE` posture is explicit
- `mock` retreat remains available
- fail-closed remains available

### B. Safety and reviewability

- host safety is still exact-origin only
- canonical env family is still `TESTNET_EXCHANGE_*`
- credential presence is proven without exposing values
- merged kill switch visibility is confirmed
- `/ops -> /commands -> /commands/[id]` review path is reachable
- logs remain supporting evidence only

### C. Attempt discipline

- one-command-only attempt remains the plan
- no automatic retry is present
- no second request is preauthorized
- ingress freeze remains intact
- no deploy/config/domain/ingress changes are mixed into the same window

### D. Retreat credibility

- retreat drill posture is understood
- dry activation posture is understood
- first anomaly means retreat, not quick retry
- evidence preservation is stronger than experimental pressure

If any one of these is not explicit, the gate stays closed.

## 6. Automatic block conditions

This gate must return `BLOCKED` immediately if any of these are true:

- runtime posture depends on inherited shell state or guesswork
- host/origin identity is not exact
- reviewer cannot confirm the review path is reachable
- command shape is still broad or not fully specified
- any participant expects a second request might happen in the same window
- any participant wants to change ingress/deploy/runtime shape “while we are there”
- packet quality depends on chat memory instead of bounded references
- retreat is described vaguely instead of as an immediate concrete action

These are not “minor concerns.” They are hard block signals.

## 7. Decision labels

Use exactly one label:

### `PASS - WINDOW MAY OPEN`

Use only if:

- all mandatory go conditions are explicitly satisfied
- no automatic block condition is present
- reviewer is willing to sign that the first request remains bounded to one real attempt
- live trading remains `NO-GO`

### `BLOCKED - WINDOW MUST STAY CLOSED`

Use if:

- any go condition is unknown
- any automatic block condition is present
- reviewer confidence depends on unstated memory
- the packet is complete on paper but not credible operationally

### `FAIL - GATE BREACHED`

Use only if:

- a runtime window is opened without this gate
- the window opens despite known block conditions
- the gate output is later shown to contradict the actual runtime posture

This label is for process breach, not normal readiness refusal.

## 8. Minimum decision gate template

Use this baseline structure:

```text
gate_id:
decision_date:
operator:
reviewer:
witness:

scheduling_packet_ref:
prereq_check_ref:
runtime_window_ref:
runtime_verification_ref:
retreat_drill_ref:

canonical_path_confirmed: yes/no
runtime_posture_explicit: yes/no
real_mode_intent_explicit: yes/no
mock_retreat_available: yes/no
fail_closed_available: yes/no

host_safety_confirmed: yes/no
canonical_env_family_confirmed: yes/no
credential_presence_confirmed: yes/no
kill_switch_visibility_confirmed: yes/no
review_path_reachable: yes/no
logs_supporting_only_confirmed: yes/no

one_command_only_confirmed: yes/no
automatic_retry_absent: yes/no
second_request_not_preauthorized: yes/no
ingress_freeze_intact: yes/no
same_window_runtime_changes_absent: yes/no

retreat_posture_credible: yes/no
evidence_preservation_credible: yes/no

decision_label:
decision_notes:
window_may_open: yes/no
```

## 9. Gate quality rules

This decision gate is only valid if:

- it can be applied from one bounded review surface
- it does not require secrets
- it keeps the decision binary enough to avoid “soft yes”
- it makes opening the window harder than writing about the window

If the process can drift into “good enough, let’s try,” the gate is too weak.

## 10. Stable status statement

At this point the correct scheduling-gate summary is:

```text
a complete scheduling packet does not open the first real request window by itself
the window opens only after an explicit reviewer gate confirms posture,
reviewability, and retreat credibility under one bounded attempt
```

## 11. Minimal next bounded round

After this decision gate, the next natural bounded round is:

```text
Real Testnet First Real Request Scheduling Gate Bundle V1
```

Scope:

```text
docs-only
collect the scheduling packet and scheduling decision gate
into one final pre-window review bundle
```

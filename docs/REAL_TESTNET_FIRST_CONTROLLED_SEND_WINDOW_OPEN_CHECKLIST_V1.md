# Real Testnet first controlled send window open checklist V1

**Status:** window-open checklist only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the exact short checklist that should be used at the moment a real candidate window is about to be opened for the first controlled real external testnet send on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not open the window by itself.
It standardizes the final minimum checks that should be explicitly confirmed immediately before the candidate window transitions into an active runtime window.

## 1. Decision

The first controlled send window should not open because “everything looked fine a few minutes ago.”

It should open only after a short final checklist confirms:

```text
the candidate window is still valid,
the runtime posture is still explicit,
the review surfaces are still reachable,
and the retreat posture is still immediate
```

If any one of those is uncertain, the window should stay closed.

## 2. Fixed applicability

This checklist applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be reused for:

- legacy `QUOTE + BINANCE_TESTNET`
- mocked executor attempts
- dry-run windows
- live trading

## 3. What this checklist is for

This checklist exists to answer one narrow question:

```text
right before opening the real candidate window,
what minimum facts must still be explicitly true
for the first controlled send to remain safe, bounded, and reviewable
```

It is not:

- the schedule packet itself
- the execution record
- the final post-send closeout

It is the final short gate between “candidate identified” and “window actually opened.”

## 4. Required source inputs

This checklist should be applied using bounded source materials:

1. candidate-window record  
   [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_V1.md)
2. runtime window spec  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md)
3. cloud host runtime verification checklist  
   [docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md)

If these are not enough to confirm the window-open moment, the window is not ready to open.

## 5. Required checks

The operator and reviewer should explicitly confirm all of these immediately before opening the window.

### A. Candidate validity

- candidate window id still matches the intended window
- host identity still matches the intended host
- runtime posture label is still the expected one
- canonical command linkage is still the intended one

### B. Runtime posture

- `TESTNET_EXECUTOR_MODE` value is still the expected value
- `TESTNET_EXECUTOR_REAL_ENABLE` value is still the expected value
- `mock` retreat remains available
- fail-closed remains available

### C. Safety boundary

- host/origin still matches expected value
- canonical env family remains correct
- credential presence remains confirmed without exposure
- kill switch visibility remains available
- ingress freeze remains intact

### D. Reviewability

- `/ops` is reachable
- `/commands` is reachable
- `/commands/[id]` is reachable
- logs will remain supporting evidence only

### E. Discipline

- one-command-only rule still holds
- no quick retry rule still holds
- second send still not preauthorized
- no unrelated ingress/deploy/config work is being mixed into this opening moment

If any of these checks is not a clean “yes,” the window should not open.

## 6. Minimum checklist template

Use this baseline structure:

```text
checklist_id:
timestamp:
operator:
reviewer:
witness:

candidate_window_id_confirmed:
host_identity_confirmed:
runtime_posture_label_confirmed:
canonical_command_linkage_confirmed:

executor_mode_value_confirmed:
real_enable_value_confirmed:
mock_retreat_available:
fail_closed_available:

host_origin_confirmed:
canonical_env_family_confirmed:
credential_presence_confirmed:
kill_switch_visibility_confirmed:
ingress_freeze_intact:

ops_reachable:
commands_reachable:
command_detail_reachable:
logs_supporting_only_confirmed:

one_command_only_confirmed:
no_quick_retry_rule_confirmed:
second_send_not_preauthorized:
no_same_window_runtime_mutation:

decision_label:
window_may_open:
notes:
```

## 7. Decision labels

Use exactly one label:

### `PASS - WINDOW MAY OPEN`

Use only if:

- every required check is answered `yes`
- the candidate remains valid
- runtime posture is still explicit
- retreat remains immediate
- live trading remains `NO-GO`

### `BLOCKED - WINDOW STAYS CLOSED`

Use if:

- any check is unknown or ambiguous
- candidate facts drifted
- reviewability is weaker than sendability
- retreat confidence is weaker than open-window confidence

### `INVALID`

Use only if:

- the window was opened without this checklist
- or the checklist later proves inconsistent with the actual runtime posture

## 8. Stable status statement

At this point the correct window-open-checklist summary is:

```text
right before the first controlled send window opens,
the project should confirm one last short checklist
covering candidate validity, runtime posture, safety boundary,
reviewability, and execution discipline
```

## 9. Minimal next bounded round

After this checklist, the next natural bounded round is:

```text
Real Testnet First Controlled Send Window Open Closeout V1
```

Scope:

```text
docs-only
record that the window-open checklist layer is now complete,
and state exactly what still separates the documentary opening posture
from the first real controlled send itself
```

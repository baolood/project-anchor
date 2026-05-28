# Real Runtime Window Proof Acquisition Plan V1

**Status:** acquisition plan only - docs-only, no baseline change, no runtime mutation, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-28**

**Scope:** translate the runtime-window proof collection packet into one bounded acquisition plan that states which proof items would be gathered first, by whom, and in what review order if the project later prepares for a real runtime window.

This plan does not authorize a real request.
It does not open a runtime window.
It only defines the safest acquisition order for the proof families that the project already knows it needs.

## 1. Decision

The project has already finished the documentary design work for runtime-window proof:

- readiness review
- evidence map
- collection packet
- fill trial

That means the next useful documentary step is no longer “what fields should exist?”
It is:

```text
if the project later prepares for a real runtime window,
what proof should be gathered first,
who should gather it,
and in what review order should that happen
so the process stays bounded and fail-closed?
```

## 2. Acquisition-plan rules

This plan must obey all of these:

1. It must keep the collection effort bounded to one canonical event.
2. It must gather cloud-host proof before any attempt to overinterpret command-side evidence.
3. It must not assume that `/commands/[id]` evidence will exist before a real command object exists.
4. It must preserve reviewer independence during reconciliation.
5. It must fail closed on missing proof.
6. `live trading` remains `NO-GO`.

## 3. Acquisition objective

The acquisition plan exists to answer one narrow question:

```text
if the team later prepares for a real runtime window,
what exact proof families should be collected in what order
so the first controlled send remains bounded and reviewable?
```

It is not:

- a send runbook
- a deployment plan
- an approval bypass
- a promise that a real request will happen

## 4. Acquisition phases

Use this acquisition order.

### Phase 1. Cloud-host readiness capture

This phase must happen first.

**Proof families to collect first**
- host identity
- revision identity
- runtime posture label
- `TESTNET_EXECUTOR_MODE`
- `TESTNET_EXECUTOR_REAL_ENABLE`
- configured origin
- host label
- kill switch state
- credential presence confirmed without exposing secrets
- `/ops` reachability
- `/commands` reachability
- `/commands/[id]` reachability expectation

**Primary owner**
- operator captures
- reviewer confirms

**Why first**
Because if cloud-host posture cannot be proven, the project should not move into deeper runtime interpretation at all.

**Stop rule**
If any required Phase 1 proof item is `NOT_COLLECTED`, acquisition stops with:

```text
BLOCKED BEFORE REAL WINDOW PROOF
```

### Phase 2. Runtime-window identity capture

Only after Phase 1 is coherent.

**Proof families to collect**
- runtime window id
- open timestamp reference
- operator identity for the bounded window
- reviewer identity for the bounded window
- explicit note that the event is still one bounded canonical attempt surface only

**Primary owner**
- operator captures
- reviewer confirms

**Why second**
Because the project needs an explicit bounded event identity before any later command-side evidence can be reconciled safely.

**Stop rule**
If runtime-window identity cannot be frozen clearly, acquisition remains:

```text
BLOCKED BEFORE EVENT RECONCILIATION
```

### Phase 3. Command-detail evidence capture

Only if a real command object exists.

**Proof families to collect**
- `command_id`
- idempotency key
- source
- created_by
- final command state
- event family
- normalized family
- external request status
- external order id, if present

**Primary owner**
- reviewer captures
- operator confirms bounded context

**Why third**
Because command-detail evidence is canonical only once the project has a real bounded event identity to attach it to.

**Stop rule**
If a real command object should exist but command-detail evidence is `NOT_COLLECTED`, acquisition remains:

```text
BLOCKED OR REVIEW_INCOMPLETE
```

### Phase 4. Cross-source reconciliation

Only after both host-side and command-side surfaces are available.

**Proof families to collect**
- host-side window identity matches command-side event identity
- operator identity consistent across records
- reviewer identity consistent across records
- timing consistent
- runtime posture consistent with command outcome
- no second request / quick retry escaped the bounded event

**Primary owner**
- final reviewer

**Why fourth**
Because reconciliation is meaningful only after the prior two evidence families exist.

**Stop rule**
If reconciliation cannot be proven, acquisition remains:

```text
BLOCKED OR REVIEW_CONTRADICTED
```

## 5. Owner sequence

The acquisition plan assumes this owner sequence.

### A. Operator sequence

The operator should move first on:
- host-side identity and posture capture
- runtime-window identity capture
- retreat readiness confirmation

### B. Reviewer sequence

The reviewer should move second on:
- host-side confirmation
- command-detail evidence capture
- event-family and normalized-family interpretation

### C. Final reviewer sequence

The final reviewer should move last on:
- cross-source reconciliation
- contradiction detection
- final blocked / incomplete / stronger reviewed posture decision

## 6. Minimal acquisition-order template

Use this baseline structure:

```text
acquisition_plan_id:
plan_date:
operator:
reviewer:
final_reviewer:
optional_witness:

canonical_path: ORDER
execution_mode: testnet

phase_1_cloud_host_readiness:
  required_items:
  owner:
  stop_rule:

phase_2_runtime_window_identity:
  required_items:
  owner:
  stop_rule:

phase_3_command_detail_capture:
  required_items:
  owner:
  stop_rule:

phase_4_reconciliation:
  required_items:
  owner:
  stop_rule:

default_if_any_phase_incomplete: BLOCKED
live_trading: NO-GO
notes:
```

## 7. Default acquisition posture

Unless stronger real evidence is actually being prepared, the default acquisition posture should remain:

```text
phase_1: not started
phase_2: not started
phase_3: not started
phase_4: not started
default_if_any_phase_incomplete: BLOCKED
live_trading: NO-GO
```

This keeps the plan descriptive rather than performative.

## 8. Current acquisition verdict

The current acquisition verdict is:

```text
READY TO PLAN, NOT READY TO CLAIM
```

Meaning:

- the project can now describe the safest acquisition order
- the project still has not collected the real proof itself
- the first controlled send remains blocked until the acquisition phases are actually satisfied

## 9. Stable status statement

At this point the correct acquisition-plan summary is:

```text
the project now knows the safest proof-acquisition order
cloud-host readiness comes first, command-detail capture comes next,
and reconciliation comes last
until those phases are actually completed, first controlled send remains BLOCKED
live trading: NO-GO
```

## 10. Minimal next bounded round

After this acquisition plan, the next natural bounded round is:

```text
Runtime Proof Readiness vs Execution Decision Review V1
```

Scope:

```text
docs-only
assess whether the project should stop documentary expansion here
and wait for real collection conditions,
or whether one more decision-layer review is still useful
```

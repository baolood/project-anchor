# Guardrail Surface Ownership Map V1

**Status:** ownership-map only - no baseline behavior change, no execution-order change, no runtime mutation, no external request, no live trading change.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-28**

**Scope:** define a bounded ownership map for the current guardrail surface so that future work can answer “who owns this surface?” before anyone responds by adding another layer.

This map does **not**:

- remove checks
- replace wrappers with real call-site changes
- authorize residency changes in the baseline
- reopen the runtime-proof line

It only assigns surface responsibilities.

## 1. Why an ownership map is needed

The inventory tells us which checks are core, supporting, or consolidation candidates.
The reading-order guide tells us how to read the surface.

What is still easy to blur is ownership:

```text
which surfaces decide current posture,
which surfaces explain lifecycle progression,
which surfaces preserve continuity,
and which surfaces carry hard-block meaning that must never be softened?
```

Without that map, later contributors may still:

- add a new closeout instead of extending an owned surface
- patch a continuity concern into a posture surface
- bury a hard block under a broader narrative wrapper

## 2. Ownership model

Use the following four ownership classes.

### A. Posture owners

These own the answer to:

```text
what is the current project decision state right now?
```

Posture owners are the first place to look before any execution or readiness discussion.

### B. Lifecycle owners

These own the answer to:

```text
how did the project move through bounded stages to reach today's posture?
```

Lifecycle owners explain sequence, but do not by themselves relax hard blocks.

### C. Continuity owners

These own the answer to:

```text
are adjacent review surfaces still internally coherent and readable?
```

Continuity owners protect review confidence, not move authority.

### D. Hard-block owners

These own the answer to:

```text
what explicitly prevents real external request expansion today?
```

Hard-block owners must remain unmistakable.
They should never be diluted into softer “workflow summary” language.

## 3. Current ownership map

### A. Repo safety frame owner

Owned surfaces:

- `scripts/check_checklist_curl_guardrails.sh`
- `scripts/check_go_live_rules.sh`
- `scripts/check_local_box_baseline.sh`

Responsibility:

- repo-level guardrail integrity
- rule-anchor integrity
- baseline execution frame

Ownership class:

- `posture owner`

Why:

- nothing downstream matters if this frame breaks

### B. First-controlled-send posture owner

Owned surfaces:

- `docs/FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLASSIFICATION_SCHEMA_V1.md`
- `docs/FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLASSIFICATION_RECORD_V1.md`
- `docs/FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLASSIFICATION_FILL_TRIAL_V1.md`
- `scripts/check_first_controlled_send_status_integration.sh`

Responsibility:

- current first-controlled-send verdict vocabulary
- current fill posture
- top-level project-facing status interpretation

Ownership class:

- `posture owner`

Why:

- this surface gives the shortest accurate answer to “where are we now?”

### C. Runtime-proof HOLD owner

Owned surfaces:

- `docs/REAL_RUNTIME_WINDOW_PROOF_READINESS_REVIEW_V1.md`
- `docs/REAL_RUNTIME_WINDOW_PROOF_EVIDENCE_MAP_V1.md`
- `docs/REAL_RUNTIME_WINDOW_PROOF_COLLECTION_PACKET_V1.md`
- `docs/REAL_RUNTIME_WINDOW_PROOF_FILL_TRIAL_V1.md`
- `docs/REAL_RUNTIME_WINDOW_PROOF_ACQUISITION_PLAN_V1.md`
- `docs/RUNTIME_PROOF_READINESS_VS_EXECUTION_DECISION_REVIEW_V1.md`

Responsibility:

- define what runtime-proof evidence is missing
- define how it would be collected
- define why docs-only preparation is now sufficient
- define why real execution remains blocked

Ownership class:

- `posture owner`
- `lifecycle owner`

Why:

- it is both a current HOLD surface and the explanation of what would have to become true before collection restarts

### D. Explicit send hard-block owner

Owned surfaces:

- `scripts/check_real_handoff_testnet_credential_runtime_presence_boundary.sh`
- `scripts/check_real_handoff_testnet_external_request_dry_approval_boundary.sh`
- `scripts/check_real_handoff_explicit_send_approval_packet_boundary.sh`
- `scripts/check_real_handoff_explicit_runtime_send_line.sh`
- grouped candidate:
  - `scripts/check_real_handoff_explicit_send_block_surface.sh`

Responsibility:

- preserve the strongest “no” around real external request progression
- keep runtime-send blocking semantics explicit
- prevent broader handoff coherence from being mistaken for send authorization

Ownership class:

- `hard-block owner`
- `posture owner`

Why:

- this surface is the clearest answer to “why can we still not send?”

### E. Real handoff lifecycle owner

Owned surfaces:

- adapter skeleton / report integration / drift
- task-input line
- credential placeholder line
- opening prereq / bundle / decision packet / signoff / task contract chain
- execution request envelope / approval gate chain
- activation preflight / intent / window / launch-gate chain
- launch packet / intent / window / approval / rollback / dispatch chain
- dry-run dispatch boundary and audit envelope

Future grouped owners:

- `check_real_handoff_opening_surface.sh`
- `check_real_handoff_activation_surface.sh`
- `check_real_handoff_launch_dispatch_surface.sh`

Responsibility:

- explain how the broader handoff path remains bounded and coherent
- preserve the ordered operational story before any real request could be contemplated

Ownership class:

- `lifecycle owner`
- partial `continuity owner`

Why:

- this is the densest lifecycle explanation surface in the current baseline

### F. First-controlled-send lifecycle owner

Owned surfaces:

- gate bundle closeout
- readiness review
- scheduling decision record
- decision bundle / closeout
- schedule packet
- candidate window record / closeout
- window open checklist / closeout / record / record closeout
- runtime verification record / closeout
- attempt record / closeout
- mocked external executor guardrail

Future grouped owners:

- `check_real_testnet_first_controlled_send_decision_surface.sh`
- `check_real_testnet_first_controlled_send_window_runtime_surface.sh`
- `check_real_testnet_first_controlled_send_attempt_review_surface.sh`

Responsibility:

- explain the bounded first-controlled-send path
- show how the project advanced through decision, window, runtime, and attempt stages without authorizing broader send behavior

Ownership class:

- `lifecycle owner`
- partial `continuity owner`

Why:

- this is the main bounded operational spine that leads into today's final review and runtime-proof HOLD

### G. Continuity-only owners

Owned surfaces:

- report integration checks
- closeout continuity checks
- alignment-only checks that do not change top-level posture

Responsibility:

- keep surrounding docs and review surfaces consistent
- reduce reviewer confusion
- catch contradictions between adjacent bounded artifacts

Ownership class:

- `continuity owner`

Why:

- these checks matter, but they should not be overloaded as move-authority surfaces

## 4. Ownership boundaries

Use these boundaries to decide where future work belongs.

### If the question is:

```text
what is today's decision state?
```

Then the owner is:

- repo safety frame
- first-controlled-send posture
- runtime-proof HOLD
- explicit send hard-block

### If the question is:

```text
how did we get here?
```

Then the owner is:

- real handoff lifecycle
- first-controlled-send lifecycle

### If the question is:

```text
are these adjacent surfaces still internally consistent?
```

Then the owner is:

- continuity-only surfaces

### If the question is:

```text
what explicitly prevents a real external request?
```

Then the owner is:

- explicit send hard-block
- runtime-proof HOLD owner

## 5. Anti-patterns this map is meant to prevent

### A. Continuity inflation

Bad pattern:

```text
discover small review ambiguity -> add another closeout doc
```

Preferred response:

- check whether the ambiguity belongs to a continuity owner first

### B. Lifecycle leakage into posture

Bad pattern:

```text
long lifecycle chain looks coherent -> assume posture has relaxed
```

Preferred response:

- check posture owners and hard-block owners first

### C. Hard-block dilution

Bad pattern:

```text
group strong blockers into a broad wrapper that hides their meaning
```

Preferred response:

- keep explicit send block semantics first-class and named

### D. New-layer reflex

Bad pattern:

```text
new concern appears -> add one more template or closeout
```

Preferred response:

- ask which owner should absorb the concern before creating a new surface

## 6. Near-term use

Use this map when deciding:

- whether a new issue belongs to posture, lifecycle, continuity, or hard-block semantics
- whether a future wrapper proposal is narrowing ownership correctly
- whether a new docs-only artifact is actually needed

## 7. Current state reminder

Nothing in this map changes the current project state:

```text
phase: HOLD_FOR_REAL_COLLECTION_CONDITIONS
docs-only expansion: STOPPED
runtime proof collection: NOT STARTED
real external request: NOT AUTHORIZED
live trading: NO-GO
```

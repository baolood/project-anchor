# Guardrail Surface Reading Order V1

**Status:** reading-order guide only - no baseline behavior change, no execution-order change, no runtime mutation, no external request, no live trading change.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-28**

**Scope:** define one bounded way to read the current guardrail surface without changing which checks run, when they run, or what they mean.

This guide does **not**:

- remove checks
- replace wrapper candidates with real call-site changes
- authorize any simplification by implication
- change the current `HOLD_FOR_REAL_COLLECTION_CONDITIONS` posture

It only answers:

```text
when a human needs to understand the current guardrail surface,
which ownership surfaces should they read first, and why?
```

## 1. Why a reading order is needed

The current baseline is not broken.

The current problem is that the baseline is now wide enough that a flat read is
expensive:

- core rules sit next to support checks
- handoff checks sit next to explicit block checks
- first-controlled-send checks sit next to repeated closeout rhythm

That means two different questions are easy to blur:

1. what is the current project posture?
2. which narrow checks happen to be listed next in the baseline?

This guide makes those questions separable.

## 2. Reading-order principles

The reading order should optimize for:

1. posture before detail
2. ownership before line count
3. hard blockers before support continuity
4. current decision state before historical accumulation

In practice:

- read the surfaces that answer "are we allowed to move?" first
- read the surfaces that explain "why are we blocked?" second
- read alignment and closeout continuity surfaces last

## 3. Recommended top-level reading order

### A. Rules and baseline core

Read first:

- `scripts/check_checklist_curl_guardrails.sh`
- `scripts/check_go_live_rules.sh`
- `scripts/check_local_box_baseline.sh`

Question answered:

```text
is the repo-level safety frame still intact before we interpret anything else?
```

Why first:

- everything downstream assumes these still hold
- if these are broken, downstream narrative detail is secondary

### B. Current first-controlled-send posture

Read second:

- `docs/FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLASSIFICATION_SCHEMA_V1.md`
- `docs/FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLASSIFICATION_RECORD_V1.md`
- `docs/FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLASSIFICATION_FILL_TRIAL_V1.md`
- `docs/RUNTIME_PROOF_READINESS_VS_EXECUTION_DECISION_REVIEW_V1.md`

Question answered:

```text
what is the current top-level decision state for first controlled send?
```

Why second:

- this is the shortest path to today's real posture
- it tells the reader that docs-only preparation is sufficient, execution is not authorized, and the line is in HOLD

### C. Explicit send hard-block surface

Read third:

- `scripts/check_real_handoff_testnet_credential_runtime_presence_boundary.sh`
- `scripts/check_real_handoff_testnet_external_request_dry_approval_boundary.sh`
- `scripts/check_real_handoff_explicit_send_approval_packet_boundary.sh`
- `scripts/check_real_handoff_explicit_runtime_send_line.sh`
- future grouped owner:
  - `scripts/check_real_handoff_explicit_send_block_surface.sh`

Question answered:

```text
why is real external request still blocked even if upstream review prep looks coherent?
```

Why third:

- this is the clearest runtime-send hard-block surface
- readers should see the strongest "no" before getting lost in broader handoff flow

### D. Runtime-proof HOLD surface

Read fourth:

- `docs/REAL_RUNTIME_WINDOW_PROOF_READINESS_REVIEW_V1.md`
- `docs/REAL_RUNTIME_WINDOW_PROOF_EVIDENCE_MAP_V1.md`
- `docs/REAL_RUNTIME_WINDOW_PROOF_COLLECTION_PACKET_V1.md`
- `docs/REAL_RUNTIME_WINDOW_PROOF_FILL_TRIAL_V1.md`
- `docs/REAL_RUNTIME_WINDOW_PROOF_ACQUISITION_PLAN_V1.md`

Question answered:

```text
what exact evidence is still missing before runtime-proof collection may start?
```

Why fourth:

- once the reader knows execution is blocked, the next useful question is what reality-side conditions are still missing
- this surface explains the difference between docs readiness and real evidence readiness

### E. Real handoff opening / activation / launch / dispatch surfaces

Read fifth:

- current narrow checks under:
  - opening
  - activation
  - launch/dispatch
- future grouped owners proposed in:
  - `docs/GUARDRAIL_SURFACE_CONSOLIDATION_WRAPPER_PROPOSAL_V1.md`

Question answered:

```text
how does the broader handoff posture remain coherent before any real send could even be contemplated?
```

Why fifth:

- these surfaces matter, but they are longer and denser
- after rules, posture, hard blockers, and runtime-proof HOLD are understood, this chain becomes easier to interpret correctly

### F. First-controlled-send decision / window / attempt surfaces

Read sixth:

- decision surface
- window/runtime surface
- attempt/review surface

Question answered:

```text
how did the project reach today's bounded first-controlled-send posture?
```

Why sixth:

- this is a lifecycle explanation surface
- it is best read once current posture and blocking semantics are already known

### G. Supporting continuity and closeout surfaces

Read last:

- report integration checks
- closeout continuity checks
- alignment surfaces that do not change top-level posture by themselves

Question answered:

```text
are the surrounding review surfaces still internally consistent?
```

Why last:

- these are important, but they should not be mistaken for primary move-authority surfaces
- reading them too early creates the illusion of progress without clarifying actual posture

## 4. Current ownership summary

Use this ownership summary when deciding where to read next.

### Core posture owners

- repo rules / baseline core
- final review classification surface
- runtime-proof decision review
- explicit send block surface

These answer:

```text
what is the current decision state?
```

### Lifecycle owners

- real handoff opening / activation / launch / dispatch
- first-controlled-send decision / window / attempt chain

These answer:

```text
how did we get to the current posture?
```

### Supporting continuity owners

- report integration
- closeout continuity
- alignment-only checks

These answer:

```text
is the surface internally coherent and reviewable?
```

## 5. Reading shortcuts for common questions

If the reader asks:

### "Can we execute a real external request now?"

Read:

1. `docs/RUNTIME_PROOF_READINESS_VS_EXECUTION_DECISION_REVIEW_V1.md`
2. `scripts/check_real_handoff_explicit_runtime_send_line.sh`
3. `scripts/check_real_handoff_explicit_send_block_surface.sh`

Expected answer today:

```text
no
```

### "Why are we still blocked?"

Read:

1. explicit send block surface
2. runtime-proof readiness review
3. runtime-proof evidence map

### "What would have to become true before this line restarts?"

Read:

1. `docs/RUNTIME_PROOF_READINESS_VS_EXECUTION_DECISION_REVIEW_V1.md`
2. `docs/REAL_RUNTIME_WINDOW_PROOF_ACQUISITION_PLAN_V1.md`

### "Which parts are governance and which parts are actual posture?"

Read:

1. `docs/GUARDRAIL_SURFACE_CONSOLIDATION_INVENTORY_V1.md`
2. this reading-order guide

## 6. Non-goals of this guide

This guide should not be used as evidence that:

- checks may now be removed
- wrappers may now replace narrow call sites
- support surfaces are unimportant
- runtime-proof HOLD has been relaxed

It is a navigation layer only.

## 7. Current state reminder

Nothing in this guide changes the current project state:

```text
phase: HOLD_FOR_REAL_COLLECTION_CONDITIONS
docs-only expansion: STOPPED
runtime proof collection: NOT STARTED
real external request: NOT AUTHORIZED
live trading: NO-GO
```

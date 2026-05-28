# Guardrail Surface Consolidation Plan V1

**Status:** plan only - no baseline behavior change, no execution-order change, no runtime mutation, no external request, no live trading change.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-28**

**Scope:** define one bounded future restructuring plan for the `scripts/check_local_box_baseline.sh` guardrail surface without changing current behavior yet.

This plan does **not**:

- delete checks
- move checks in the current execution order
- change baseline pass/fail behavior
- authorize simplification by implication

It only defines how future simplification should be sequenced.

## 1. Planning goal

The goal is not to make the project “lighter” in a vague way.

The goal is to make the guardrail surface easier to reason about while preserving the current fail-closed posture.

That means future consolidation must improve at least one of these:

- ownership clarity
- reading order
- baseline explainability
- review confidence

without weakening:

- hard runtime-send blocks
- first-controlled-send posture tracking
- rules enforcement
- review-surface consistency

## 2. Current problem statement

From the inventory:

- baseline references **52** `check_*.sh` files
- `real_handoff_*` alone accounts for **27**
- `real_testnet_first_controlled_send_*` accounts for **15**

The current risk is not that these checks are “wrong”.
The risk is:

```text
the baseline is now wide enough that future contributors may add one more
surface instead of understanding which surfaces are core, which are support,
and which should be grouped behind a clearer ownership boundary
```

## 3. Future target shape

The future target shape should be:

### A. Core always-on baseline

A relatively small group that directly answers:

- is the repo baseline intact?
- are the rules intact?
- is the current real-testnet posture still hard-blocked where expected?
- is the first-controlled-send decision spine still coherent?

### B. Supporting always-on baseline

A second group that remains in baseline for now, but is explicitly documented as:

- review-surface continuity
- closeout integrity
- alignment checks

These stay always-on until grouped replacements exist.

### C. Grouped handoff surface

Instead of a long flat chain of nearby `real_handoff_*` contract checks, the future shape should move toward:

- one grouped opening surface
- one grouped activation surface
- one grouped launch surface
- one grouped dispatch surface
- one grouped approval-boundary surface

Each grouped surface may still call narrower checks internally.
The key change is ownership shape, not immediate logic deletion.

### D. Grouped first-controlled-send closeout surface

The future shape should move toward:

- decision path core
- window/runtime/attempt path core
- one grouped closeout/evidence surface

The repeated `record -> closeout` rhythm should stay understandable, but it does not need to stay visually flat in the top-level baseline forever.

## 4. Non-goals

This plan explicitly does **not** recommend:

- deleting narrow checks immediately
- reducing the number of checks just to make counts smaller
- replacing docs-only checks with runtime-side behavior
- merging unlike concepts just because they are adjacent

In particular, it does **not** recommend removing:

- `check_real_handoff_explicit_runtime_send_line.sh`
- `check_real_testnet_external_executor_mocked_v1.sh`
- `check_real_testnet_first_controlled_send_schedule_packet.sh`
- `check_real_testnet_first_controlled_send_window_open_record.sh`
- `check_real_testnet_first_controlled_send_runtime_verification_record.sh`
- `check_real_testnet_first_controlled_send_attempt_record.sh`

before a clearer grouped ownership structure exists.

## 5. Sequenced consolidation plan

### Phase 1 - Label the surface without behavior change

Status:

```text
ready now
```

Deliverables:

- inventory document
- plan document
- future naming convention for grouped surfaces

Allowed changes:

- docs only

Disallowed changes:

- baseline behavior change
- script removal
- script movement

### Phase 2 - Introduce grouped wrapper entrypoints

Status:

```text
future
```

Deliverables:

- one grouped wrapper for `real_handoff` opening/activation
- one grouped wrapper for `real_handoff` launch/dispatch
- one grouped wrapper for `first_controlled_send` closeout/evidence surfaces

Allowed changes:

- add wrapper scripts
- keep old narrow checks intact underneath
- baseline may call grouped wrappers only after output parity is demonstrated

Disallowed changes:

- deleting underlying narrow checks in the same round

Success test:

- grouped wrapper output is strictly equivalent or more readable
- baseline result is unchanged

### Phase 3 - Reclassify baseline residency

Status:

```text
future, after grouped wrappers prove stable
```

Deliverables:

- explicit `core always-on`
- explicit `supporting always-on`
- explicit `grouped internally-called`

Allowed changes:

- baseline top-level call list becomes shorter
- grouped wrappers absorb some narrow call sites

Disallowed changes:

- reclassification without documentation
- residency changes mixed with runtime or project-scope changes

### Phase 4 - Evaluate retirement candidates

Status:

```text
future, only after at least one stable cycle with grouped wrappers
```

Deliverables:

- very small candidate list of checks whose intent is now fully owned elsewhere

Allowed changes:

- targeted retirement proposals

Disallowed changes:

- mass deletion
- “remove because it feels redundant”

## 6. Immediate recommendations by surface

### `real_handoff_*`

Recommended next shape:

- group by lifecycle:
  - opening
  - activation
  - launch
  - dispatch
  - explicit-send hard block

Reason:

- this family has the highest flat-check density
- most of the current friction is cognitive, not logical

### `real_testnet_first_controlled_send_*`

Recommended next shape:

- keep the decision spine visible
- group repeated closeout/evidence checks behind one future wrapper

Reason:

- this family is more coherent than `real_handoff_*`
- the main issue is repeated closeout layering, not conceptual confusion

### baseline core

Recommended next shape:

- preserve a small unmistakable top-level policy core

That core should continue to foreground:

- checklist curl guardrails
- rules SSOT enforcement
- first-controlled-send status integration
- hard runtime-send block
- mocked external executor gate

## 7. Success criteria for future consolidation

Any later consolidation round should only be accepted if all of these remain true:

1. `scripts/check_local_box_baseline.sh` still returns the same PASS/FAIL outcome on the same repo state.
2. No hard runtime-send barrier becomes less explicit.
3. No first-controlled-send state transition becomes harder to explain.
4. Reviewers can identify `core` checks faster than before.
5. A contributor is less tempted to add “one more layer” because grouped ownership is clearer.

## 8. Recommended next bounded round

After this plan, the next useful bounded round is:

```text
Guardrail Surface Consolidation Wrapper Proposal V1
```

Scope:

```text
docs-only
name the first grouped wrapper candidates,
map old check names to grouped wrapper ownership,
and define what parity evidence will be required
before any baseline call-site change is allowed
```

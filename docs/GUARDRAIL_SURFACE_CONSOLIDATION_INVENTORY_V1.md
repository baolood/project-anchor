# Guardrail Surface Consolidation Inventory V1

**Status:** inventory only - no baseline behavior change, no runtime mutation, no external request, no live trading change.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-28**

**Scope:** classify the current `scripts/check_local_box_baseline.sh` guardrail surface into four buckets so future simplification can be deliberate instead of reactive:

- `core`
- `supporting`
- `consolidate`
- `do_not_remove_yet`

This inventory does **not** delete checks, change execution order, or change baseline pass/fail behavior.

## 1. Why this inventory exists

The baseline has grown into a wide review-and-safety surface.

That growth has mostly come from the right place:

- bounded docs-only gates
- fixture matrices
- review-surface alignment
- closeout posture checks

But the current shape now creates a different risk:

```text
people may respond to uncertainty by adding one more layer
instead of understanding which existing layers are truly core,
which are supporting evidence,
and which now need structural consolidation
```

This inventory is meant to slow that pattern down.

## 2. Current baseline shape

At the time of this inventory, `scripts/check_local_box_baseline.sh` references **52** `check_*.sh` scripts.

High-level clustering:

- `real_handoff_*`: 27
- `real_testnet_first_controlled_send_*`: 15
- `real_credential_*`: 1
- checklist/baseline/core misc: 9

This is no longer a “small baseline”.
It is now a policy surface.

## 3. Classification rules

### `core`

Use when removing the check from the always-on baseline would meaningfully weaken:

- baseline integrity
- rules enforcement
- active project posture
- the canonical first-controlled-send decision path

### `supporting`

Use when the check mainly protects:

- review readability
- cross-surface consistency
- documentation alignment
- bounded evidence continuity

These are still valuable, but they are not always the first line of defense.

### `consolidate`

Use when the check looks useful but is a candidate for future grouping, folding, or ownership narrowing because:

- naming overlap is high
- nearby checks form a chain that may be too granular
- the same protective intent is spread across too many adjacent files

This is **not** a deletion label.
It is a future redesign label.

### `do_not_remove_yet`

Use when the check may look redundant or overly narrow, but removal is premature because:

- it protects a still-fragile transition
- its upstream or downstream neighbors are not yet structurally simplified
- the project would lose review confidence if it disappeared before a replacement grouping exists

## 4. `core`

These should continue to be treated as default always-on baseline gates for now.

### Baseline and rules core

- `scripts/check_checklist_curl_guardrails.sh`
- `scripts/check_go_live_rules.sh`
- `scripts/check_first_controlled_send_status_integration.sh`

Why:

- they protect baseline execution assumptions
- they enforce the rules SSOT
- they provide the currently active summary posture for first-controlled-send work

### First controlled send path core

- `scripts/check_real_testnet_first_real_request_gate_bundle_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_readiness_review.sh`
- `scripts/check_real_testnet_first_controlled_send_scheduling_decision_record.sh`
- `scripts/check_real_testnet_first_controlled_send_decision_bundle.sh`
- `scripts/check_real_testnet_first_controlled_send_schedule_packet.sh`
- `scripts/check_real_testnet_first_controlled_send_candidate_window_record.sh`
- `scripts/check_real_testnet_first_controlled_send_window_open_checklist.sh`
- `scripts/check_real_testnet_first_controlled_send_window_open_record.sh`
- `scripts/check_real_testnet_first_controlled_send_runtime_verification_record.sh`
- `scripts/check_real_testnet_first_controlled_send_attempt_record.sh`

Why:

- together they form the main bounded decision and evidence path
- they represent the operational spine of the current first-controlled-send posture
- they are the least ambiguous “where are we now?” checks in the chain

### Hard-block runtime-send core

- `scripts/check_real_handoff_explicit_runtime_send_line.sh`
- `scripts/check_real_testnet_external_executor_mocked_v1.sh`

Why:

- they are direct barriers around real external request expansion
- they express the current hard-block posture more clearly than many narrower upstream fixtures

## 5. `supporting`

These still add value, but their primary role is to keep the review surface coherent rather than define the project’s top-level posture by themselves.

### First controlled send closeout/evidence support

- `scripts/check_real_testnet_first_controlled_send_decision_bundle_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_candidate_window_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_window_open_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_window_open_record_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_runtime_verification_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_attempt_closeout.sh`

Why:

- these mostly preserve docs-only closeout consistency
- they are useful, but they read more like evidence wrappers than core gating pivots

### Real handoff review-surface support

- `scripts/check_real_handoff_adapter_report_integration.sh`
- `scripts/check_real_handoff_adapter_runtime_fixture_drift.sh`
- `scripts/check_real_handoff_task_input_line.sh`
- `scripts/check_real_credential_placeholder_line.sh`
- `scripts/check_real_handoff_opening_prereq_line.sh`
- `scripts/check_real_handoff_opening_bundle_line.sh`
- `scripts/check_real_handoff_opening_decision_packet_line.sh`

Why:

- these are valuable because they keep adjacent review surfaces aligned
- they are less about “system may now proceed” and more about “reviewers should not see contradictions”

## 6. `consolidate`

These are the clearest future candidates for structural grouping or chain folding.

### Real handoff contract ladder

- `scripts/check_real_handoff_opening_signoff_packet_contract.sh`
- `scripts/check_real_handoff_opening_task_contract.sh`
- `scripts/check_real_handoff_execution_request_envelope_contract.sh`
- `scripts/check_real_handoff_execution_request_approval_gate_contract.sh`
- `scripts/check_real_handoff_executor_activation_preflight_contract.sh`
- `scripts/check_real_handoff_executor_activation_intent_contract.sh`
- `scripts/check_real_handoff_executor_activation_window_contract.sh`
- `scripts/check_real_handoff_executor_activation_launch_gate_contract.sh`
- `scripts/check_real_handoff_executor_launch_packet_contract.sh`
- `scripts/check_real_handoff_executor_launch_intent_contract.sh`
- `scripts/check_real_handoff_executor_launch_window_contract.sh`
- `scripts/check_real_handoff_executor_launch_approval_gate_contract.sh`
- `scripts/check_real_handoff_executor_launch_rollback_packet_contract.sh`
- `scripts/check_real_handoff_executor_final_dispatch_preflight_contract.sh`
- `scripts/check_real_handoff_executor_dry_run_dispatch_boundary.sh`
- `scripts/check_real_handoff_dry_run_dispatch_audit_envelope.sh`
- `scripts/check_real_handoff_testnet_credential_runtime_presence_boundary.sh`
- `scripts/check_real_handoff_testnet_external_request_dry_approval_boundary.sh`
- `scripts/check_real_handoff_explicit_send_approval_packet_boundary.sh`

Why:

- they form a very granular ladder of nearby intent/packet/window/approval concepts
- the protective logic is legitimate, but the ownership surface is long and cognitively expensive
- this is the strongest consolidation candidate in the current baseline

### First controlled send repeating pattern

- `scripts/check_real_testnet_first_controlled_send_decision_bundle_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_candidate_window_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_window_open_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_window_open_record_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_runtime_verification_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_attempt_closeout.sh`

Why:

- these are consistent and understandable, but they repeat the same `record -> closeout` rhythm many times
- this likely wants a future grouped “closeout surface” abstraction, even if today’s scripts stay separate

## 7. `do_not_remove_yet`

These are the checks that may tempt future simplification too early.

- `scripts/check_real_handoff_adapter_skeleton.sh`
- `scripts/check_real_handoff_explicit_runtime_send_line.sh`
- `scripts/check_real_testnet_first_real_request_gate_bundle_closeout.sh`
- `scripts/check_real_testnet_first_controlled_send_schedule_packet.sh`
- `scripts/check_real_testnet_first_controlled_send_window_open_record.sh`
- `scripts/check_real_testnet_first_controlled_send_runtime_verification_record.sh`
- `scripts/check_real_testnet_first_controlled_send_attempt_record.sh`
- `scripts/check_real_testnet_external_executor_mocked_v1.sh`

Why:

- each protects a currently fragile transition point
- some are ugly but strategically important
- simplification should happen around them, not by casually removing them first

## 8. Immediate conclusions

### What this inventory says clearly

1. The baseline is now a real policy surface, not a lightweight smoke wrapper.
2. `real_handoff_*` is the biggest consolidation candidate.
3. `first_controlled_send_*` is structurally clearer, but its closeout density is rising.
4. The right next move is not “add another layer by default”.
5. The right next move is to begin explicit layered ownership of the existing guardrail surface.

### What this inventory does **not** say

- it does not say the baseline should be reduced immediately
- it does not say current checks are useless
- it does not authorize removal
- it does not change execution order

## 9. Recommended next bounded round

After this inventory, the next useful bounded round is:

```text
Guardrail Surface Consolidation Plan V1
```

Scope:

```text
docs-only
propose one future restructuring of baseline checks into:
- core always-on
- supporting always-on
- grouped handoff surface
- grouped first-controlled-send closeout surface
without changing runtime behavior yet
```

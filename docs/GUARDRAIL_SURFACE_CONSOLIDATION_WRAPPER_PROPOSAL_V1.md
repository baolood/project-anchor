# Guardrail Surface Consolidation Wrapper Proposal V1

**Status:** wrapper proposal only - no baseline behavior change, no execution-order change, no runtime mutation, no external request, no live trading change.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-28**

**Scope:** define the first grouped-wrapper candidates for the current guardrail surface, map existing narrow checks into future grouped ownership, and state what parity evidence will be required before any baseline call-site change is allowed.

This proposal does **not**:

- add wrapper scripts yet
- delete narrow checks
- change baseline pass/fail behavior
- change baseline call order

## 1. Why wrappers are the next step

The inventory and plan already establish that:

- the baseline is now a policy surface
- `real_handoff_*` is the densest flat chain
- `first_controlled_send_*` is clearer, but its repeated closeout layering is growing

What is still missing is one practical bridge between:

```text
we know which surfaces should eventually be grouped
```

and:

```text
we know exactly which grouped wrappers would own which narrow checks
```

Without that bridge, future simplification risks turning into vague “clean up the baseline” work.

## 2. Wrapper design rules

Any future grouped wrapper should obey all of these:

1. It must group a real ownership surface, not just reduce line count.
2. It must keep the current fail-closed semantics explicit.
3. It must call existing narrow checks first before any retirement discussion begins.
4. It must emit clearer top-level meaning than the current flat list.
5. It must not blur hard runtime-send blockers into softer narrative wrappers.

## 3. Proposed wrapper set

### A. `check_real_handoff_opening_surface.sh`

Future ownership:

- `check_real_handoff_adapter_skeleton.sh`
- `check_real_handoff_adapter_report_integration.sh`
- `check_real_handoff_adapter_runtime_fixture_drift.sh`
- `check_real_handoff_task_input_line.sh`
- `check_real_credential_placeholder_line.sh`
- `check_real_handoff_opening_prereq_line.sh`
- `check_real_handoff_opening_bundle_line.sh`
- `check_real_handoff_opening_decision_packet_line.sh`
- `check_real_handoff_opening_signoff_packet_contract.sh`
- `check_real_handoff_opening_task_contract.sh`

Intent:

- unify the pre-executor opening posture
- keep early review surfaces together
- make “can the handoff opening surface even be considered coherent?” a first-class question

### B. `check_real_handoff_activation_surface.sh`

Future ownership:

- `check_real_handoff_execution_request_envelope_contract.sh`
- `check_real_handoff_execution_request_approval_gate_contract.sh`
- `check_real_handoff_executor_activation_preflight_contract.sh`
- `check_real_handoff_executor_activation_intent_contract.sh`
- `check_real_handoff_executor_activation_window_contract.sh`
- `check_real_handoff_executor_activation_launch_gate_contract.sh`

Intent:

- group the executor-activation transition
- stop scattering “activation” across envelope, approval, preflight, intent, and window language

### C. `check_real_handoff_launch_dispatch_surface.sh`

Future ownership:

- `check_real_handoff_executor_launch_packet_contract.sh`
- `check_real_handoff_executor_launch_intent_contract.sh`
- `check_real_handoff_executor_launch_window_contract.sh`
- `check_real_handoff_executor_launch_approval_gate_contract.sh`
- `check_real_handoff_executor_launch_rollback_packet_contract.sh`
- `check_real_handoff_executor_final_dispatch_preflight_contract.sh`
- `check_real_handoff_executor_dry_run_dispatch_boundary.sh`
- `check_real_handoff_dry_run_dispatch_audit_envelope.sh`

Intent:

- group the launch-to-dispatch lifecycle into one obvious ownership surface
- keep rollback, approval, and dry-run dispatch tied to the same operational story

### D. `check_real_handoff_explicit_send_block_surface.sh`

Future ownership:

- `check_real_handoff_testnet_credential_runtime_presence_boundary.sh`
- `check_real_handoff_testnet_external_request_dry_approval_boundary.sh`
- `check_real_handoff_explicit_send_approval_packet_boundary.sh`
- `check_real_handoff_explicit_runtime_send_line.sh`

Intent:

- isolate the hard runtime-send block as its own unmistakable top-level surface
- prevent the current strongest blocker from being buried inside a larger grouped wrapper

### E. `check_real_testnet_first_controlled_send_decision_surface.sh`

Future ownership:

- `check_real_testnet_first_real_request_gate_bundle_closeout.sh`
- `check_real_testnet_first_controlled_send_readiness_review.sh`
- `check_real_testnet_first_controlled_send_scheduling_decision_record.sh`
- `check_real_testnet_first_controlled_send_decision_bundle.sh`
- `check_real_testnet_first_controlled_send_decision_bundle_closeout.sh`
- `check_real_testnet_first_controlled_send_schedule_packet.sh`

Intent:

- keep the pre-scheduling and scheduling decision spine visible as one grouped ownership surface
- preserve the answer to “where are we before any window opens?”

### F. `check_real_testnet_first_controlled_send_window_runtime_surface.sh`

Future ownership:

- `check_real_testnet_first_controlled_send_candidate_window_record.sh`
- `check_real_testnet_first_controlled_send_candidate_window_closeout.sh`
- `check_real_testnet_first_controlled_send_window_open_checklist.sh`
- `check_real_testnet_first_controlled_send_window_open_closeout.sh`
- `check_real_testnet_first_controlled_send_window_open_record.sh`
- `check_real_testnet_first_controlled_send_window_open_record_closeout.sh`
- `check_real_testnet_first_controlled_send_runtime_verification_record.sh`
- `check_real_testnet_first_controlled_send_runtime_verification_closeout.sh`

Intent:

- group the candidate-window to verified-window lifecycle
- keep the operational spine visible while absorbing the repeated closeout rhythm into one wrapper owner

### G. `check_real_testnet_first_controlled_send_attempt_review_surface.sh`

Future ownership:

- `check_real_testnet_first_controlled_send_attempt_record.sh`
- `check_real_testnet_first_controlled_send_attempt_closeout.sh`
- `check_real_testnet_external_executor_mocked_v1.sh`

Intent:

- group the current attempted-event review posture
- keep the mocked executor gate visibly adjacent to the attempt-review surface until real review artifacts are stronger

## 4. Proposed future top-level baseline shape

This is only a target sketch, not a change request.

Future top-level baseline shape could become:

1. baseline/rules core
2. first-controlled-send status integration
3. real handoff opening surface
4. real handoff activation surface
5. real handoff launch/dispatch surface
6. explicit send block surface
7. first controlled send decision surface
8. first controlled send window/runtime surface
9. first controlled send attempt/review surface

That is still a substantial baseline, but it is a smaller set of ownership surfaces than the current flat 52-check list.

## 5. Parity evidence required before any call-site change

No baseline call-site change should be allowed until all of these are demonstrated.

### A. Narrow-check preservation

The grouped wrapper must call every currently-owned narrow check.

Required proof:

- exact child-check list recorded in the wrapper docstring or companion docs

### B. Output parity

The grouped wrapper must preserve the same effective failure surface.

Required proof:

- on the same repo state, grouped wrapper PASS/FAIL matches the old narrow call chain

### C. Human readability improvement

The grouped wrapper must make baseline output easier to interpret, not just shorter.

Required proof:

- top-level summary meaning is more obvious than the current flat chain

### D. Hard-block preservation

Any grouped surface touching runtime-send blockers must keep those blockers explicit.

Required proof:

- no grouped wrapper hides or renames away the current hard-block semantics

### E. One stable cycle before retirement talk

Old narrow checks should not become removal candidates in the same round that grouped wrappers are introduced.

Required proof:

- at least one stable local + CI cycle with wrappers in place first

## 6. Wrappers that should stay separate longest

These should be the last to disappear into anything broader:

- `check_real_handoff_explicit_runtime_send_line.sh`
- `check_real_testnet_external_executor_mocked_v1.sh`
- `check_real_testnet_first_controlled_send_schedule_packet.sh`
- `check_real_testnet_first_controlled_send_window_open_record.sh`
- `check_real_testnet_first_controlled_send_runtime_verification_record.sh`
- `check_real_testnet_first_controlled_send_attempt_record.sh`

Reason:

- they are current transition anchors
- they carry high explanatory value even before any future regrouping

## 7. Immediate recommendation

The next useful implementation round should **not** jump directly to removing or relocating checks.

The next useful implementation round should instead:

1. choose exactly one grouped wrapper candidate
2. implement it as a pure wrapper
3. prove parity locally
4. keep existing narrow checks intact

The best first candidate is:

```text
check_real_handoff_explicit_send_block_surface.sh
```

Why:

- it is conceptually narrow
- it owns the clearest hard-block posture
- it is lower-risk than attempting to group the whole opening or launch ladders first

## 8. Recommended next bounded round

After this wrapper proposal, the next useful bounded round is:

```text
Guardrail Surface Consolidation First Wrapper Trial V1
```

Scope:

```text
docs-plus-script
introduce one grouped wrapper without changing baseline call order yet,
prove it can own the current narrow checks cleanly,
and keep all existing narrow checks intact
```

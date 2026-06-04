# G5 k6 Provisioning Decision And Authorization Review V1

## 1. Current G5 state

- capacity and stress test row: `IN_PROGRESS`
- `G5 — Capacity/stress test at target load pass`: `NOT_DONE`
- execution packet prepared: `YES`
- capacity execution may start now: `NO`
- current blocker: `K6_NOT_PRESENT_ON_STAGE`
- CT-02 executed: `NO`
- CT-03 executed: `NO`

## 2. Decision result

Current decision:

- `k6` provisioning path selected: `YES`
- `k6` installation authorized in a future bounded task: `YES`
- exact `k6` version to be pinned at install time: `YES`
- capacity execution authorized by this review: `NO`

## 3. Selected provisioning path

Selected first bounded provisioning posture:

- install target: stage host only
- install purpose: first bounded G5 CT-02 / CT-03 execution
- installation retention posture: retain on the stage host after install unless a
  later cleanup task explicitly removes it
- version policy: capture and record the exact installed `k6 version` output in
  the provisioning evidence and reuse that version for the first bounded run

This is intentionally narrower than a general tooling rollout.

## 4. Why this path is selected

This path is selected because:

- the current blocker is host-local tool absence, not runtime health
- G5 execution depends on repeatable staged-ramp semantics
- version drift would make CT-02 / CT-03 evidence harder to compare or rerun
- a stage-host-only install keeps the change bounded away from backend, worker,
  secrets, branch protection, and production systems

## 5. Required provisioning evidence

The future bounded provisioning task must capture:

- host identity
- repo path
- pre-install `k6 version` failure or absence signal
- exact install method used
- post-install `k6 version` output
- whether the tool is retained on host after install
- confirmation that no CT-02 / CT-03 run was executed during provisioning

## 6. Mandatory stop conditions

The future provisioning task must stop immediately if:

- stage host identity is unclear
- the install method would mutate backend / worker / docker / runtime config
- the install method would require changing secrets
- the exact resulting `k6 version` cannot be captured
- the task drifts into actual CT-02 / CT-03 execution
- any action would become a real external request or live trading path

## 7. Status after this review

- provisioning decision review prepared: `YES`
- `k6` install authorized in a future bounded task: `YES`
- exact `k6` version already captured: `NO`
- `k6` present on stage now: `NO`
- capacity execution may start now: `NO`
- `G5` ready for `DONE`: `NO`

## 8. Boundary

- `k6` installed by this review: `NO`
- CT-02 executed by this review: `NO`
- CT-03 executed by this review: `NO`
- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`

## 9. Explicit non-claims

- this review does not install `k6`
- this review does not execute CT-02
- this review does not execute CT-03
- this review does not complete the Week 5-6 capacity row
- this review does not complete `G5`

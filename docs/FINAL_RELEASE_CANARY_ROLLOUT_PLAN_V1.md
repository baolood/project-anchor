# Final Release Canary Rollout Plan V1

## 1. Current release state

- `G1 — Deployment and rollback drills pass`: `DONE`
- `G2 — P0/P1 alerting verified`: `DONE`
- `G3 — Backup/restore drill within RPO/RTO`: `DONE`
- `G4 — Security review complete`: `DONE`
- `G5 — Capacity/stress test at target load pass`: `DONE`
- `G6 — On-call roster + incident SOP active`: `DONE`
- selected next release mainline: `Canary/gradual rollout plan executed`
- canary rollout executed by this plan: `NO`
- release freeze executed by this plan: `NO`
- production launch executed by this plan: `NO`

## 2. Fixed boundary

- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`
- production overwrite: `NO`

## 3. Bounded canary shape fixed now

The first release rollout must use a bounded canary sequence rather than a
single-step full launch.

The fixed rollout shape is:

1. pre-window readiness check
2. canary step 1: `5%` traffic equivalent or smallest enforceable bounded slice
3. watch window 1
4. canary step 2: `25%` traffic equivalent
5. watch window 2
6. canary step 3: `50%` traffic equivalent
7. watch window 3
8. full release only after explicit final go/no-go approval

This plan intentionally separates canary planning from the later release freeze
and final launch decision.

## 4. Watch window fixed now

The minimum watch posture for each step is:

- watch window fixed: `YES`
- minimum watch window per step: `30 min`
- required surfaces during each watch:
  - `/health`
  - `/ops/state`
  - `/ops/worker`
  - alert channel for `P0/P1`
  - agreed SLI/SLO dashboard or captured metric set

## 5. Abort thresholds fixed now

Abort the rollout immediately if any of the following occurs:

- control-plane health endpoints are not stably reachable
- a `P0` alert fires
- a `P1` alert fires and is not downgraded with evidence
- error-rate exceeds the agreed SLO envelope
- latency exceeds the agreed SLO envelope
- worker heartbeat disappears or becomes stale
- rollback trigger is reached but rollback authority is unclear

## 6. Rollback posture fixed now

The rollout rollback posture is:

- rollback trigger fixed: `YES`
- rollback authority during rollout: `Release manager / on-call primary`
- rollback method source: `docs/ROLLBACK_DRILL_RUNBOOK.md`
- rollback expectation: revert to the last known healthy release state before continuing any rollout

## 7. Required future execution evidence

The future canary execution task must capture non-secret evidence for:

- exact canary window start/end times
- exact traffic slice used at each step
- watch window results at each step
- health and ops endpoint results
- alert state during each watch window
- explicit rollback or continue decision after each step
- final PASS / FAIL verdict for canary execution

## 8. What is still not done

This plan still does **not** prove:

- canary rollout executed: `NO`
- release freeze executed: `NO`
- final go/no-go signoff executed: `NO`
- production launch executed: `NO`

## 9. Status after this plan

- canary rollout plan prepared: `YES`
- canary rollout executed: `NO`
- watch window fixed: `YES`
- abort thresholds fixed: `YES`
- rollback trigger fixed: `YES`
- release freeze executed: `NO`
- production launch executed: `NO`
- go-live ready now: `NO`
- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`

## 10. Explicit non-claims

- this plan does not execute canary rollout
- this plan does not declare release freeze
- this plan does not perform final go/no-go signoff
- this plan does not authorize production launch
- this plan does not authorize real external requests
- this plan does not authorize live trading

# G5 Clean Post-Run Recovery Verification Rerun Closeout V1

## 1. Current G5 state before rerun

- capacity and stress test row: `IN_PROGRESS`
- `G5 — Capacity/stress test at target load pass`: `NOT_DONE`
- first bounded capacity execution verdict: `FAIL`
- refined blocker before this rerun: `CLEAN_POST_RUN_RECOVERY_EVIDENCE_MISSING`

## 2. Execution identity

- stage host: `vultr`
- repo path: `/root/project-anchor`
- stage repo revision observed during rerun: `0fe4a86`
- run id: `20260604T091506Z`
- artifact directory: `/root/project-anchor/artifacts/go-live/capacity/20260604T091506Z`
- exact `k6` version:
  - `k6 v2.0.0 (commit/8c3be52cc1, go1.26.3, linux/amd64)`

## 3. Pre-run baseline

Observed before CT-02 began:

- `/health`: reachable, `{"ok":true}`
- `/ops/state`: reachable
- `/ops/worker`: reachable
- worker heartbeat visible: `YES`
- kill switch enabled: `NO`

## 4. CT-02 rerun result

- target sustained rate: `3 RPS`
- observed request rate: `3.0011020048239487/s`
- total requests: `2701`
- HTTP failures observed: `0`
- checks succeeded: `100%`
- observed p95 request duration: `3.806947ms`

Immediate post-CT-02 recovery verification:

- retry 1 `/health`: `PASS`
- retry 1 `/ops/state`: `PASS`
- retry 1 `/ops/worker`: `PASS`
- retry 2 `/health`: `PASS`
- retry 2 `/ops/state`: `PASS`
- retry 2 `/ops/worker`: `PASS`
- retry 3 `/health`: `PASS`
- retry 3 `/ops/state`: `PASS`
- retry 3 `/ops/worker`: `PASS`

CT-02 rerun verdict:

- bounded peak segment result: `PASS`
- immediate recovery verification result: `PASS`

## 5. CT-03 rerun result

- observed request rate across staged ramp: `4.049967746583362/s`
- total requests: `2430`
- HTTP failures observed: `0`
- checks succeeded: `100%`
- observed p95 request duration: `3.911461549999998ms`

Observed degradation behavior:

- no HTTP failure spike was observed during the bounded ramp
- no SLO breach was directly observed inside the `k6` request metrics
- no worker stall was observed during the load window
- the read-only control-plane mix remained stable through the bounded stress ramp

Immediate post-CT-03 recovery verification:

- retry 1 `/health`: `PASS`
- retry 1 `/ops/state`: `PASS`
- retry 1 `/ops/worker`: `PASS`
- retry 2 `/health`: `PASS`
- retry 2 `/ops/state`: `PASS`
- retry 2 `/ops/worker`: `PASS`
- retry 3 `/health`: `PASS`
- retry 3 `/ops/state`: `PASS`
- retry 3 `/ops/worker`: `PASS`

CT-03 rerun verdict:

- bounded stress segment result: `PASS`
- immediate recovery verification result: `PASS`

## 6. Final G5 result

- CT-02 executed: `YES`
- CT-03 executed: `YES`
- degradation behavior documented: `YES`
- post-run recovery cleanly verified: `YES`
- first bounded capacity rerun verdict: `PASS`
- Week 5-6 capacity row ready for `DONE`: `YES`
- `G5 — Capacity/stress test at target load pass`: `DONE`

## 7. Boundary

- runtime config changed by this rerun: `NO`
- secrets changed by this rerun: `NO`
- deploy changed by this rerun: `NO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`
- go-live: `NO-GO`

## 8. Evidence this closeout proves

This rerun proves that:

- the approved `k6` execution path works on the stage host
- CT-02 target load completed within the bounded read-only control-plane profile
- CT-03 bounded stress ramp completed within the bounded read-only
  control-plane profile
- degradation behavior is documented and acceptable for the approved bounded run
- immediate post-run recovery verification can be captured cleanly

## 9. Explicit non-claims

- this closeout does not authorize go-live
- this closeout does not authorize real external requests
- this closeout does not authorize live trading

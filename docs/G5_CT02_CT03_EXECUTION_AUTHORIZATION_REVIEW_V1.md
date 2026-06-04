# G5 CT-02 / CT-03 Execution Authorization Review V1

## 1. Current G5 state

- capacity and stress test row: `IN_PROGRESS`
- `G5 — Capacity/stress test at target load pass`: `NOT_DONE`
- load tool selected: `k6`
- first bounded execution profile fixed: `read-only control-plane mix`
- exact `k6` version captured already: `YES`
- `k6` present on stage now: `YES`
- capacity execution may start now: `YES`
- CT-02 executed: `NO`
- CT-03 executed: `NO`

## 2. Authorization result

Current review result:

- CT-02 execution authorized in a future bounded task: `YES`
- CT-03 execution authorized in a future bounded task: `YES`
- combined CT-02 / CT-03 bounded execution may proceed: `YES`
- `G5` ready for `DONE` now: `NO`

This review authorizes the first bounded execution only. It does not claim that
the tests have already passed or that degradation behavior has already been
captured.

## 3. Authorized bounded execution shape

The authorized first bounded run is:

- target host: the current stage host already used in G5 preflight
- tool: installed host-local `k6`
- profile: read-only control-plane mix
- CT-02: `3 RPS` sustained for `15 min`
- CT-03: staged ramp beginning at `1 RPS` until first SLO breach, then bounded
  hold up to `5 min`

The authorized scope remains limited to:

- `/health`
- `/ops/state`
- `/ops/worker`

No write-path, trading-path, or external-request surface is authorized by this
review.

## 4. Required evidence before and during execution

The future execution task must capture:

- exact `k6 version`
- stage host identity
- pre-run `/health`
- pre-run `/ops/state`
- pre-run `/ops/worker`
- CT-02 command and summary
- CT-03 command and summary
- post-CT-02 `/health`
- post-CT-02 `/ops/state`
- post-CT-03 `/health`
- post-CT-03 `/ops/state`
- post-CT-03 `/ops/worker`
- observed p95 latency
- observed error rate
- observed degradation mode
- final PASS / FAIL verdict

## 5. Mandatory stop conditions

The future bounded execution must stop immediately if:

- `/health` is not healthy before CT-02 starts
- `/ops/state` is not reachable before CT-02 starts
- `/ops/worker` is not reachable before CT-02 starts
- worker heartbeat is already stale before the run
- exact `k6 version` cannot be captured at run time
- sustained 5xx responses appear before planned CT-03 breach observation
- worker freshness breaches or worker stalls occur outside the planned bounded
  breach window
- any step drifts into real external request or live trading behavior

## 6. Boundary

- runtime config changed by this review: `NO`
- secrets changed by this review: `NO`
- CT-02 executed by this review: `NO`
- CT-03 executed by this review: `NO`
- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`

## 7. Status after this review

- execution authorization review prepared: `YES`
- CT-02 execution authorized in a future bounded task: `YES`
- CT-03 execution authorized in a future bounded task: `YES`
- combined CT-02 / CT-03 bounded execution may proceed: `YES`
- capacity evidence collected already: `NO`
- degradation behavior documented already: `NO`
- `G5` ready for `DONE`: `NO`

## 8. Explicit non-claims

- this review does not execute CT-02
- this review does not execute CT-03
- this review does not prove target-load safety
- this review does not complete the Week 5-6 capacity row
- this review does not complete `G5`

# G5 First Bounded Capacity Execution Closeout V1

## 1. Current G5 state before execution

- capacity and stress test row: `IN_PROGRESS`
- `G5 — Capacity/stress test at target load pass`: `NOT_DONE`
- load tool selected: `k6`
- exact `k6` version captured already: `YES`
- `k6` present on stage now: `YES`
- CT-02 executed: `NO`
- CT-03 executed: `NO`
- `G5` ready for `DONE`: `NO`

## 2. Execution identity

- stage host: `vultr`
- repo path: `/root/project-anchor`
- stage repo revision observed during run: `0fe4a86`
- run id: `20260604T081518Z`
- artifact directory: `/root/project-anchor/artifacts/go-live/capacity/20260604T081518Z`
- exact `k6` version:
  - `k6 v2.0.0 (commit/8c3be52cc1, go1.26.3, linux/amd64)`

## 3. Pre-run baseline

Observed before CT-02 began:

- `/health`: reachable, `{"ok":true}`
- `/ops/state`: reachable
- `/ops/worker`: reachable
- worker heartbeat visible: `YES`
- kill switch enabled: `NO`

## 4. CT-02 result

CT-02 bounded peak run executed against the approved read-only control-plane
mix.

- target sustained rate: `3 RPS`
- actual observed request rate: `3.0011/s`
- total requests: `2701`
- HTTP failures observed: `0`
- checks succeeded: `100%`
- observed p95 request duration: `3.86ms`
- observed max request duration: `16.28ms`

CT-02 verdict:

- bounded peak segment result: `PASS`

## 5. CT-03 result

CT-03 bounded stress ramp executed against the approved read-only control-plane
mix.

- observed request rate across staged ramp: `4.049981/s`
- total requests: `2430`
- HTTP failures observed: `0`
- checks succeeded: `100%`
- observed p95 request duration: `3.83ms`
- observed max request duration: `8.67ms`

Observed degradation behavior:

- no HTTP failure spike was observed during the bounded ramp
- no SLO breach was directly observed inside the `k6` request metrics
- no worker stall was observed during the load window itself

CT-03 verdict:

- bounded stress segment result: `PASS`

## 6. Post-run recovery result

Post-run recovery evidence was not clean:

- the first immediate post-run endpoint checks returned empty / failed
- a subsequent direct diagnostic `curl -v` to `/health` returned `HTTP/1.1 200 OK`
- later follow-up retries for `/health`, `/ops/state`, and `/ops/worker` again
  returned empty / failed results
- read-only runtime inspection still showed:
  - port `127.0.0.1:8000` listening
  - `anchor-backend-backend-1` container `Up`
  - `anchor-backend-worker-1` container `Up`
  - `uvicorn app.main:app` process present
  - `python -m app.workers.domain_command_worker` process present

This means the load phases themselves completed successfully, but the post-run
recovery surface remained unstable / not cleanly verified.

## 7. Boundary

- runtime config changed by this execution: `NO`
- secrets changed by this execution: `NO`
- deploy changed by this execution: `NO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`
- go-live: `NO-GO`

## 8. Final result for this closeout

- CT-02 executed: `YES`
- CT-03 executed: `YES`
- degradation behavior documented: `YES`
- post-run recovery cleanly verified: `NO`
- first bounded capacity execution verdict: `FAIL`
- `G5` ready for `DONE`: `NO`

Reason for fail verdict:

- `POST_RUN_RECOVERY_UNSTABLE`

## 9. Next required step

The next bounded G5 task is:

- perform a read-only post-run recovery investigation
- determine why control-plane endpoints were intermittently unavailable after the
  load run even though container/process presence remained intact
- re-run bounded CT-02 / CT-03 only after the recovery behavior is explained or
  corrected

## 10. Explicit non-claims

- this closeout does not mark the Week 5-6 capacity row `DONE`
- this closeout does not mark `G5` `DONE`
- this closeout does not authorize go-live
- this closeout does not authorize real external requests
- this closeout does not authorize live trading

# G5 Traffic Profile And Load Tool Decision V1

## 1. Current G5 state

- capacity and stress test row: `IN_PROGRESS`
- `G5 — Capacity/stress test at target load pass`: `NOT_DONE`
- stage / prod-like host available for future bounded execution: `YES`
- CT-02 executed: `NO`
- CT-03 executed: `NO`

## 2. Decision result

Selected first bounded G5 execution shape:

- load tool: `k6`
- load tool posture: pinned single-binary runner for repeatable scripted stages
- selected traffic profile type: read-only operator/control-plane mix
- selected worker component treatment: ambient background only, not synthetic job creation

## 3. Why this tool

`k6` is selected because it gives us:

- explicit staged ramp definitions for CT-02 / CT-03
- simple threshold expressions that map cleanly to SLO-style pass/fail language
- reproducible text output suitable for docs-backed evidence

This is a better fit than ad hoc single-endpoint tools for the first bounded G5
run because we need both:

- mixed read-only traffic
- auditable degradation thresholds

## 4. Selected first traffic profile

The first bounded G5 profile is intentionally limited to read-only surfaces that
already exist and are already part of our health / ops / alert evidence chain.

### Endpoint mix

| Surface | Share | Method | Payload shape | Why included |
|---|---:|---|---|---|
| `/health` | `50%` | `GET` | tiny JSON (`{\"ok\": true}`) | availability probe surface; highest-frequency cheap read |
| `/ops/state` | `30%` | `GET` | moderate JSON with kill switch, worker heartbeat, recent ops state | operational visibility surface already used by synthetic checks and alerts |
| `/ops/worker` | `20%` | `GET` | small JSON with `telegram_enabled` + last heartbeat | worker-liveness/control-plane surface already used in alerting evidence |

### Worker / background assumption

- worker background activity is treated as ambient stage runtime load
- the first bounded G5 run does **not** create synthetic commands or external-request-like traffic
- no write-path or mutating API endpoint is part of the first profile

## 5. Expected peak source

Current expected peak RPS source for the first bounded G5 run:

- source type: `bounded engineering estimate`
- expected peak RPS: `2`
- CT-02 target sustained RPS: `3`

Reason:

- the current stage is still operator-mediated, not public traffic
- the selected first profile is intentionally scoped to control-plane read paths
- this gives us a real but conservative first peak run without pretending we
  already have customer-derived traffic analytics

This does **not** claim the final production traffic model is settled.
It only fixes the first bounded G5 gate profile.

## 6. CT-02 / CT-03 staging decision

Planned first bounded execution posture:

- CT-02: sustain `3 RPS` total for `15 min`
- CT-03: ramp from `1 RPS` upward in staged steps until first SLO breach, then
  hold the breach point for `5 min`

Observed pass/fail must still be judged against:

- SLO-1 availability
- SLO-2 latency
- SLO-4 worker freshness

## 7. What must still happen later

Still required before `G5` can move to `DONE`:

1. pin the exact `k6` version in the execution packet
2. define the concrete script artifact location
3. execute CT-02 against stage
4. execute CT-03 against stage
5. record degradation behavior and recovery action

## 8. Boundary

- load test executed by this decision: `NO`
- runtime changed by this decision: `NO`
- real external request authorized: `NO`
- live trading: `NO-GO`
- go-live: `NO-GO`
- `G5` ready for `DONE`: `NO`

## 9. Explicit non-claims

- this decision does not execute CT-02
- this decision does not execute CT-03
- this decision does not prove target-load safety
- this decision does not complete the Week 5-6 capacity row
- this decision does not complete `G5`

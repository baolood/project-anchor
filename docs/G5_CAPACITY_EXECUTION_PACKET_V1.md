# G5 Capacity Execution Packet V1

## 1. Current G5 state

- capacity and stress test row: `IN_PROGRESS`
- `G5 — Capacity/stress test at target load pass`: `NOT_DONE`
- load tool selected: `k6`
- first bounded execution profile fixed: read-only control-plane mix
- CT-02 executed: `NO`
- CT-03 executed: `NO`

## 2. First bounded execution packet

This packet prepares the first real bounded G5 run without executing it.

Planned execution order:

1. preflight host identity + health check
2. `k6` version capture
3. CT-02 peak run
4. bounded steady-state verification
5. CT-03 stress ramp run
6. degradation / recovery observation
7. closeout evidence bundle

## 3. Fixed execution parameters

### Tool and version evidence

- load generator: `k6`
- exact version pin rule: capture `k6 version` output immediately before the
  run and copy that exact string into the run evidence
- this packet does not claim a version has already been captured

### Traffic mix

- `/health`: `50%`
- `/ops/state`: `30%`
- `/ops/worker`: `20%`

### CT-02 target

- total sustained RPS: `3`
- duration: `15 min`
- purpose: first bounded peak confirmation against current stage control-plane
  surfaces

### CT-03 target

- ramp start: `1 RPS`
- ramp pattern: staged increments until first SLO breach
- breach hold window: `5 min`
- hard stop: error rate `> 5%` or worker freshness breach / worker stall

## 4. Preflight evidence that must exist before execution

The future execution task must collect all of the following before starting:

- stage host identity
- repo revision on stage
- container health baseline
- `/health` baseline response
- `/ops/state` baseline response
- `/ops/worker` baseline response
- current worker heartbeat visibility
- exact `k6 version`

If any of these is missing, the run must stop before CT-02 begins.

## 5. Run commands to be captured later

The future bounded execution task should capture exact command lines and outputs
for:

- `k6 version`
- CT-02 command
- CT-03 command
- post-CT-02 `/health`
- post-CT-02 `/ops/state`
- post-CT-03 `/health`
- post-CT-03 `/ops/state`
- post-CT-03 `/ops/worker`

This packet deliberately does not invent final shell lines yet if the stage-side
script location or invocation wrapper is still unset.

## 6. Result storage and evidence format

Result location for the future run:

- `artifacts/go-live/capacity/<date>/`

Minimum evidence bundle items:

- `k6` version capture
- CT-02 summary
- CT-03 summary
- observed p95 latency
- observed error rate
- observed degradation mode
- observed worker heartbeat behavior
- recovery action, if any
- final PASS / FAIL verdict

## 7. Stop conditions

The future execution must stop immediately if:

- stage host identity is unclear
- `/health` is not healthy before the run
- `/ops/state` is not reachable before the run
- worker heartbeat is already stale before the run
- exact `k6` version cannot be recorded
- runtime starts returning sustained 5xx or worker freshness breaches before the
  planned CT-03 breach hold
- any action would become a real external request or live trading path

## 8. Current result after this packet

- execution packet prepared: `YES`
- exact `k6` version captured already: `NO`
- CT-02 executed: `NO`
- CT-03 executed: `NO`
- degradation evidence collected: `NO`
- `G5` ready for `DONE`: `NO`

## 9. Boundary

- load test executed by this packet: `NO`
- runtime changed by this packet: `NO`
- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`

## 10. Explicit non-claims

- this packet does not execute CT-02
- this packet does not execute CT-03
- this packet does not prove target-load safety
- this packet does not complete the Week 5-6 capacity row
- this packet does not complete `G5`

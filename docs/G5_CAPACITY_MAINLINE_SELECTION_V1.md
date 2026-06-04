# G5 Capacity Mainline Selection V1

## 1. Current G5 state

- capacity and stress test row: `IN_PROGRESS`
- `G5 — Capacity/stress test at target load pass`: `NOT_DONE`
- stage / prod-like host evidence available: `YES`
- `G1 — Deployment and rollback drills pass`: `DONE`
- `G2 — P0/P1 alerting verified`: `DONE`
- `G3 — Backup/restore drill within RPO/RTO`: `DONE`
- `G4 — Security review complete`: `DONE`

## 2. Remaining blocker inventory for G5

From `docs/CAPACITY_TEST_PLAN.md`, the main unresolved blockers are:

1. §3 traffic profile still contains placeholder rows
2. expected peak RPS is not yet fixed
3. load generator / pinned tool choice is not yet fixed
4. no CT-02 peak run evidence exists
5. no CT-03 degradation evidence exists

## 3. Selected next G5 mainline

Selected next mainline:

- `Traffic profile and load-tool decision`

Status:

- selected G5 mainline status: `NOT_DONE`

## 4. Why this is next

This is the highest-value next step because:

- CT-02 and CT-03 cannot be executed honestly until the traffic mix is defined
- a peak/stress result without an agreed traffic profile would not be auditable
- tool choice must be pinned before results can be compared or rerun

In other words:

- execution is not the blocker yet
- execution-definition quality is the blocker

## 5. What must not happen yet

The following should not happen yet:

- do not run a capacity test against stage
- do not claim CT-02 or CT-03 evidence exists
- do not mark the Week 5-6 capacity row `DONE`
- do not mark `G5` `DONE`

## 6. Next task boundary

Next task:

- `G5 Traffic Profile And Load Tool Decision V1`

That task should remain docs-only and should:

1. choose the first bounded load generator
2. define the initial endpoint / worker mix
3. define expected peak RPS source and placeholder-free values
4. prepare the exact future CT-02 / CT-03 evidence surface

Allowed files for the next task:

- `docs/G5_TRAFFIC_PROFILE_AND_LOAD_TOOL_DECISION_V1.md`
- `docs/CAPACITY_TEST_PLAN.md`
- `docs/GO_LIVE_CHECKLIST.md`

Forbidden actions for the next task:

- no real load generation
- no runtime mutation
- no deploy / rollback execution
- no live trading
- no real external request authorization

## 7. Boundary

- capacity test executed by this selection: `NO`
- degradation evidence collected by this selection: `NO`
- `G5` ready for `DONE`: `NO`
- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`

## 8. Explicit non-claims

- this selection does not execute CT-02
- this selection does not execute CT-03
- this selection does not complete the Week 5-6 capacity row
- this selection does not complete `G5`
- this selection does not authorize go-live
- this selection does not authorize live trading
- this selection does not authorize real external requests

# Final Release Mainline Selection V1

## 1. Current fixed completed hard gates

- `G1 — Deployment and rollback drills pass`: `DONE`
- `G2 — P0/P1 alerting verified`: `DONE`
- `G3 — Backup/restore drill within RPO/RTO`: `DONE`
- `G4 — Security review complete`: `DONE`
- `G5 — Capacity/stress test at target load pass`: `DONE`
- `G6 — On-call roster + incident SOP active`: `DONE`

## 2. Still-forbidden boundary

- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`
- production overwrite: `NO`

## 3. Remaining release execution inventory

Reading the current checklist, the remaining not-done release execution items are:

- `Canary/gradual rollout plan executed`
- `Release freeze + go/no-go review`
- `Production launch completed`
- `T-2: verify alerts, on-call roster, escalation contacts`
- `T-1: final go/no-go review and signoff`
- `T (launch): canary rollout + watch SLO/alerts for agreed window`
- `T+1: post-launch review, open follow-up actions, close launch ticket`

## 4. Selected next mainline

The single selected next release mainline is:

- `Canary/gradual rollout plan executed`

No other release mainline is selected before that item is prepared.

## 5. Why this is next

This is the highest-priority remaining release item because:

- it is the first remaining execution row in checklist order
- it defines the exact bounded path between hard-gate completion and any future launch motion
- the release freeze and final go/no-go review depend on a concrete rollout shape
- production launch cannot safely proceed before the canary path, watch window, and rollback expectations are fixed

What is still missing now:

- canary scope
- traffic step sequence
- watch window
- abort thresholds
- rollback trigger and rollback authority during rollout

What must not happen yet:

- no release freeze declaration
- no final go/no-go signoff
- no production launch
- no real external request
- no live trading

## 6. Next bounded task

The next task must remain docs-only:

- `Final Release Canary Rollout Plan V1`

Allowed files:

- `docs/FINAL_RELEASE_CANARY_ROLLOUT_PLAN_V1.md`
- `docs/GO_LIVE_CHECKLIST.md`

Forbidden files/actions:

- do not modify runtime code
- do not modify backend / worker / risk / deploy / docker / env / scripts / CI
- do not execute rollout
- do not declare release freeze
- do not perform final go/no-go signoff
- do not launch production
- do not authorize real external request
- do not authorize live trading

Validation expectations for that next task:

- `git diff --check`
- prove the selected release mainline remains canary execution planning only
- keep `go-live: NO-GO`

Acceptance expectations for that next task:

- bounded rollout shape fixed
- watch / abort / rollback expectations fixed
- release freeze still not executed
- production launch still not executed

Rollback method for that next task:

- revert the docs-only commit or drop the unmerged PR branch

## 7. Explicit non-claims

- this selection does not execute rollout
- this selection does not declare release freeze
- this selection does not perform final go/no-go signoff
- this selection does not authorize production launch
- this selection does not authorize real external requests
- this selection does not authorize live trading

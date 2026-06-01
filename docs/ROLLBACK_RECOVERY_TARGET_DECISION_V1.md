# Rollback Recovery Target Decision V1

## Status

- Decision type: rollback recovery target decision
- Week 2 rollback drill completion decision: YES, once the agreed recovery target is fixed and compared to observed evidence
- Real external request authorized: NO
- Live trading: NO-GO

## Question

What is the agreed recovery target for the Week 2 rollback drill, and does the recorded destructive rollback execution satisfy it?

## Decision

Agreed recovery target:

- total rollback recovery wall time must be **<= 10 minutes**

Reasoning:

- the current rollback drill is a stage-host validation for bounded backend/worker recovery, not a production-wide incident response benchmark
- the runbook already used `<= 10 min` as the explicit example target
- a 10-minute ceiling is conservative enough to be meaningful, while still realistic for the current single-host stage topology

## Evidence used

Recorded destructive rollback execution evidence:

- source: `docs/ROLLBACK_DRILL_FIRST_DESTRUCTIVE_EXECUTION_CLOSEOUT_V1.md`
- rollback start: `2026-06-01T02:12:03+00:00`
- rollback end: `2026-06-01T02:12:29+00:00`
- total recovery wall time: `26` seconds
- target revision reached: `d76bb0a`
- `/health`: PASS
- `/ops/state`: PASS
- `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh`: PASS
- `bash scripts/check_go_live_rules.sh`: PASS

## Comparison

- agreed recovery target: `<= 10 minutes`
- observed destructive rollback recovery time: `26 seconds`
- result: `PASS`

Interpretation:

- the first destructive rollback execution completed within the agreed recovery target
- the drill now satisfies the Week 2 acceptance item `Recovery under agreed limit`

## Boundary

This decision does **not** authorize:

- real external request
- live trading
- production execution mode change
- any new rollback action beyond the already recorded drill

The following remain true:

- Real external request: NOT AUTHORIZED
- Live trading: NO-GO
- Go-live: NO-GO

## Final decision

- Agreed rollback recovery target fixed: YES
- Destructive rollback execution meets agreed target: YES
- Week 2 rollback drill completion may be marked DONE: YES
- Real external request authorized: NO
- Live trading: NO-GO

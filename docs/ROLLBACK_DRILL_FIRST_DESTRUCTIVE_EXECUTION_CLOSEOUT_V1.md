# Rollback Drill First Destructive Execution Closeout V1

## Scope

- Validation type: first destructive rollback execution drill
- Target host: Vultr Project Anchor stage host
- Public IP: `45.76.190.109`
- Hostname: `vultr`
- Repo path: `/root/project-anchor`
- Backend compose path: `/root/project-anchor/anchor-backend`
- Real external request authorized: NO
- Live trading: NO-GO

## Precheck

- Collection timestamp: `2026-06-01T02:09:55+00:00`
- Host identity: PASS
- Repo path visible: PASS
- Current deployed revision before rollback: `deda43e`
- Git dirty state recorded: `anchor-backend/docker-compose.override.yml`
- `python3` visible: `Python 3.10.12`
- `python3.11` visible: `Python 3.11.0rc1`
- Docker runtime visible: PASS
- Backend health reachable before rollback: PASS (`{"ok":true}`)
- Ops state reachable before rollback: PASS
- Kill switch before rollback: `false`
- Worker heartbeat before rollback: fresh

## Destructive rollback execution result

- Rollback action executed: YES
- Authorized rollback target: `d76bb0a`
- Final host revision after rollback: `d76bb0a`
- Checkout-based rollback path used: YES
- Bounded deploy path executed after checkout: YES

Observed timing:

- rollback start: `2026-06-01T02:12:03+00:00`
- checkout complete: `2026-06-01T02:12:03+00:00`
- rollback end: `2026-06-01T02:12:29+00:00`
- total recovery wall time: `26` seconds

Operational interpretation:

- destructive rollback path completed: YES
- rollback target reached: YES
- recovery timing captured: YES

## Postcheck

- Postcheck snapshot time: `2026-06-01T02:12:48+00:00`
- Backend visible after rollback: YES
- Worker visible after rollback: YES
- Backend status after rollback: `Up`
- Worker status after rollback: `Up`
- Backend `StartedAt`: `2026-06-01T02:12:16.33162871Z`
- Worker `StartedAt`: `2026-06-01T02:12:29.290877595Z`
- `/health` after rollback: PASS (`{"ok":true}`)
- `/ops/state` after rollback: PASS
- Kill switch after rollback: `false`
- Worker heartbeat after rollback: fresh at `2026-06-01T02:12:29.833443Z`
- `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh`: PASS (`BASELINE_RC=0`)
- `bash scripts/check_go_live_rules.sh`: PASS (`GO_LIVE_RULES_RC=0`)
- Git state after rollback: detached `HEAD` at `d76bb0a`
- Dirty file after rollback: `anchor-backend/docker-compose.override.yml`

## Boundary result

- Credential changed: NO
- `.env` changed: NO
- Kill switch changed: NO
- New command created: NO
- Real external request: NOT AUTHORIZED
- Live trading: NO-GO
- Runtime mutation outside the authorized rollback path: NO

## Interpretation

This first destructive rollback execution proves:

- the stage host can be moved from `deda43e` to the explicitly named rollback target `d76bb0a`
- the bounded deploy path can be executed successfully after the rollback checkout
- backend and worker can return to healthy visible state after the rollback execution
- the parent baseline still passes under `PYTHON=python3.11`
- go-live rules still pass after the rollback execution
- recovery timing can be captured as evidence

This closeout does **not** yet prove:

- that the drill is under an already agreed recovery target, because the agreed target is still unfilled in `docs/ROLLBACK_DRILL_RUNBOOK.md`
- real external request readiness
- live trading readiness

## Final decision

- First destructive rollback execution drill: PASS
- Rollback target reached: YES
- Recovery timing captured: YES
- Week 2 rollback drill completed: NO
- Remaining blocker to Week 2 DONE: explicitly record the agreed recovery target and confirm that the observed `26` seconds is within that agreed limit
- Real external request authorized: NO
- Live trading: NO-GO

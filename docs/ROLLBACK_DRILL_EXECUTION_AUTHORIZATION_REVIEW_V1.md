# Rollback Drill Execution Authorization Review V1

## Status

- Review type: execution authorization review only
- First destructive rollback execution drill authorized: YES
- Rollback execution performed by this document: NO
- Runtime change performed by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Background

The project has already completed:

- one-command deployment runbook validation
- rollback drill authorization review
- rollback drill first controlled validation in decision-only mode

Current evidence:

- `One-command deployment runbook validated`: DONE
- `Rollback drill completed`: still `IN_PROGRESS`
- decision-only rollback drill closeout exists:
  - `docs/ROLLBACK_DRILL_FIRST_CONTROLLED_VALIDATION_CLOSEOUT_V1.md`
- rollback drill runbook exists:
  - `docs/ROLLBACK_DRILL_RUNBOOK.md`
- rollback policy path exists:
  - `docs/RELEASE_BRANCH_POLICY.md`
- current `main` contains the decision-only rollback drill closeout:
  - `0b9691e Merge pull request #28 from baolood/chore/rollback-drill-first-validation-closeout`

The remaining blocker to Week 2 rollback completion is now narrow:

- execute one destructive rollback path in a controlled drill
- collect post-rollback smoke
- record recovery timing

## Authorization question

Should the project authorize the first destructive rollback execution drill in stage?

## Decision

Authorization decision: YES.

The project may proceed to one destructive rollback execution drill task, using the exact boundaries and stop conditions below.

This authorization does not authorize:

- real external request
- live trading
- credential changes
- kill switch changes
- production execution mode changes
- unrelated runtime repair
- unrelated package upgrades

## Authorized rollback execution scope

The next rollback execution drill task may authorize:

- SSH to the target stage host
- read-only precheck collection
- one explicitly named destructive rollback action
- read-only postcheck collection
- recovery timing capture
- rollback closeout recording

The rollback execution drill must stay inside stage host scope.

Current target host:

- Provider / role: Vultr Project Anchor stage host
- Public IP: `45.76.190.109`
- Hostname: `vultr`
- Repo path: `/root/project-anchor`
- Backend compose path: `/root/project-anchor/anchor-backend`

## Authorized rollback target

Current deployed host checkout identified during the decision-only drill:

- current deployed revision: `deda43e`

Current destructive rollback target for the first execution drill:

- rollback target revision: `d76bb0a`

Interpretation:

- `d76bb0a` is the previous host-visible merge revision before the current deployed checkout identified during the first controlled validation
- the first execution drill must treat this target as fixed unless a separate authorization explicitly changes it

## Authorized rollback path

Only one destructive path is authorized for the first execution drill:

### Authorized path A — checkout-based stage-host rollback to explicit target revision

The next task may:

1. collect the required precheck
2. move the stage host checkout from `deda43e` to `d76bb0a`
3. execute the bounded stage deploy path against that rollback target
4. collect post-rollback smoke
5. record total recovery timing

This review does **not** authorize:

- tag creation
- release note mutation
- `main` history rewrite
- `git push`
- GitHub revert PR creation

### Not authorized for the first execution drill

The following rollback paths remain unauthorized in this step:

- `git revert -m 1 <merge commit>` on `main`
- rollback target changes without separate approval
- ad hoc container-only recovery that is not tied to the named rollback target

## Required precheck before destructive rollback

Before any rollback action is executed, the next task must collect:

```bash
hostname
date -Is
cd /root/project-anchor
pwd
git rev-parse --short HEAD
git status -sb
python3 --version || true
python3.11 --version || true
which python3 || true
which python3.11 || true
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker inspect anchor-backend-backend-1 --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}} StartedAt={{.State.StartedAt}}' || true
docker inspect anchor-backend-worker-1 --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}} StartedAt={{.State.StartedAt}}' || true
curl -sS http://127.0.0.1:8000/health || true
curl -sS http://127.0.0.1:8000/ops/state || true
```

The task must stop before rollback execution if the precheck shows:

- unexpected host
- missing repo path
- current revision is not `deda43e` and no explicit operator re-approval is present
- unclear dirty state
- missing Docker runtime visibility
- backend health not reachable and no explicit operator approval to proceed
- ops state not reachable and no explicit operator approval to proceed

## Required postcheck after destructive rollback

After the destructive rollback execution, collect:

```bash
cd /root/project-anchor
git rev-parse --short HEAD
git status -sb
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker inspect anchor-backend-backend-1 --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}} StartedAt={{.State.StartedAt}}' || true
docker inspect anchor-backend-worker-1 --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}} StartedAt={{.State.StartedAt}}' || true
curl -sS http://127.0.0.1:8000/health || true
curl -sS http://127.0.0.1:8000/ops/state || true
PYTHON=python3.11 bash scripts/check_local_box_baseline.sh
bash scripts/check_go_live_rules.sh
```

## Hard boundaries

The first destructive rollback execution drill is not allowed to perform:

- real external request
- live trading
- credential changes
- `.env` changes
- kill switch changes
- new command creation
- production execution mode change
- unrelated package upgrades
- unrelated deploy changes
- runtime repair unrelated to the named rollback target
- rollback target substitution without explicit re-approval

The following must remain true:

- Real external request: NOT AUTHORIZED
- Live trading: NO-GO
- Go-live: NO-GO

## Success criteria

The first destructive rollback execution drill may be marked PASS only if all are true:

- target host identity confirmed
- repo path confirmed
- current deployed revision confirmed as `deda43e` before rollback
- rollback target confirmed as `d76bb0a`
- destructive rollback action executed
- bounded deploy path executed against the rollback target
- postcheck completed
- final host revision matches the rollback target or the variance is explicitly recorded
- `/health` remains OK or failure is explicitly recorded
- `/ops/state` remains reachable or failure is explicitly recorded
- `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh` passes
- `bash scripts/check_go_live_rules.sh` passes
- total recovery wall time recorded
- no credential change occurred
- no kill switch change occurred unless separately authorized and recorded
- no new command was created
- real external request remains NOT AUTHORIZED
- live trading remains NO-GO

## Failure handling

If the destructive rollback execution drill fails:

1. Stop.
2. Do not improvise recovery.
3. Collect visible runtime state.
4. Record the failure point.
5. Record whether rollback partially applied.
6. Do not create commands.
7. Do not change credentials.
8. Do not change kill switch.
9. Keep real external request NOT AUTHORIZED.
10. Keep live trading NO-GO.

Failure closeout must state:

```text
[Rollback Drill Execution Failure]
failure point:
current revision before rollback:
target rollback revision:
rollback action:
rollback partially applied: YES/NO
backend status:
worker status:
health result:
ops state result:
baseline result:
go-live rules result:
recovery time captured: YES/NO
operator decision:
- continue: NO
- recovery action authorized: YES/NO
real external request: NOT AUTHORIZED
live trading: NO-GO
```

## Final authorization result

- First destructive rollback execution drill authorization: YES
- Rollback execution performed by this document: NO
- Authorized rollback target: `d76bb0a`
- Authorized rollback path: checkout-based rollback to named target + bounded redeploy path
- Recommended next task: Rollback Drill First Destructive Execution Validation
- Real external request authorized: NO
- Live trading: NO-GO

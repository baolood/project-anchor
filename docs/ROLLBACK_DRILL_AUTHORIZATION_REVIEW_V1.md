# Rollback Drill Authorization Review V1

## Status

- Review type: authorization review only
- First controlled rollback drill authorized: YES
- Rollback drill executed by this document: NO
- Runtime change performed by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Background

The Week 2 one-command deployment validation has completed successfully.

Current evidence:

- `One-command deployment runbook validated`: DONE
- First controlled stage deploy validation closeout exists:
  - `docs/ONE_COMMAND_DEPLOYMENT_RUNBOOK_FIRST_CONTROLLED_VALIDATION_CLOSEOUT_V1.md`
- Hardened stage deploy runbook exists:
  - `docs/STAGE_DEPLOY_RUNBOOK.md`
- Current `main` contains the deploy validation closeout:
  - `2955713 Merge pull request #26 from baolood/chore/one-command-deploy-validation-closeout`
- Main CI after closeout:
  - `26715884677` completed success

This review answers whether the project may proceed to the first controlled rollback drill.

## Authorization question

Should the project authorize the first controlled rollback drill in stage?

## Decision

Authorization decision: YES.

The project may proceed to one controlled rollback drill task, using the boundaries and stop conditions below.

This authorization does not authorize real external request, live trading, credential changes, kill switch changes, production execution mode changes, or unrelated runtime repair.

## Authorized rollback drill scope

The next rollback drill task may authorize:

- SSH to the target stage host
- read-only precheck collection
- rollback drill execution using a bounded, explicitly named rollback action
- read-only postcheck collection
- rollback closeout recording

The rollback drill must stay inside stage host scope.

Current target host:

- Provider / role: Vultr Project Anchor stage host
- Public IP: `45.76.190.109`
- Hostname: `vultr`
- Repo path: `/root/project-anchor`
- Backend compose path: `/root/project-anchor/anchor-backend`

## Required precheck before rollback drill

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
- unclear git state
- missing Docker runtime visibility
- backend health not reachable and no explicit operator approval to proceed
- ops state not reachable and no explicit operator approval to proceed

## Rollback drill candidate action

The rollback drill must use one explicitly selected rollback action.

Allowed candidate for the first drill:

No-op rollback decision drill with runtime state preservation.

Meaning:

- collect precheck
- confirm latest deploy state
- identify the rollback target and command that would be used
- do not actually revert code unless a separate task explicitly authorizes a destructive rollback
- collect postcheck
- record whether the rollback path is operationally clear

The first rollback drill should not revert the working deployment unless the operator explicitly upgrades the drill from decision-only to execution drill.

## Not authorized in the first rollback drill

The first rollback drill is not allowed to perform:

- real external request
- live trading
- credential changes
- `.env` changes
- kill switch changes
- new command creation
- production execution mode change
- unrelated package upgrades
- unrelated deploy changes
- emergency recovery actions without a rollback decision record

The following must remain true:

- Real external request: NOT AUTHORIZED
- Live trading: NO-GO
- Go-live: NO-GO

## Required postcheck

After the rollback drill action or decision-only drill, collect:

```bash
cd /root/project-anchor
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker inspect anchor-backend-backend-1 --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}} StartedAt={{.State.StartedAt}}' || true
docker inspect anchor-backend-worker-1 --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}} StartedAt={{.State.StartedAt}}' || true
curl -sS http://127.0.0.1:8000/health || true
curl -sS http://127.0.0.1:8000/ops/state || true
PYTHON=python3.11 bash scripts/check_local_box_baseline.sh
bash scripts/check_go_live_rules.sh
git status -sb
```

## Success criteria

The first controlled rollback drill may be marked PASS only if all are true:

- target host identity confirmed
- repo path confirmed
- git revision and dirty state recorded
- current runtime state visible
- rollback target identified
- rollback action explicitly recorded as decision-only or execution drill
- postcheck completed
- `/health` remains OK or failure is explicitly recorded
- `/ops/state` remains reachable or failure is explicitly recorded
- `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh` passes
- `bash scripts/check_go_live_rules.sh` passes
- no credential change occurred
- no kill switch change occurred unless separately authorized and recorded
- no new command was created
- real external request remains NOT AUTHORIZED
- live trading remains NO-GO

## Failure handling

If the rollback drill fails:

1. Stop.
2. Do not improvise recovery.
3. Collect visible runtime state.
4. Record the failure point.
5. Do not create commands.
6. Do not change credentials.
7. Do not change kill switch.
8. Keep real external request NOT AUTHORIZED.
9. Keep live trading NO-GO.

Failure closeout must state:

```text
[Rollback Drill Failure]
failure point:
rollback target:
rollback action:
backend status:
worker status:
health result:
ops state result:
baseline result:
go-live rules result:
operator decision:
- continue: NO
- recovery action authorized: YES/NO
real external request: NOT AUTHORIZED
live trading: NO-GO
```

## Final authorization result

- First controlled rollback drill authorization: YES
- Rollback drill executed by this document: NO
- Recommended next task: Rollback Drill First Controlled Validation
- Real external request authorized: NO
- Live trading: NO-GO

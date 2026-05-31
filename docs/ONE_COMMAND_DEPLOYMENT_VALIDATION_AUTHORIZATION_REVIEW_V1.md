# One-command Deployment Validation Authorization Review V1

## Status

- Review type: authorization review only
- Stage deploy validation authorized: YES
- Authorization scope: one controlled validation of the hardened stage deploy runbook
- Deploy executed by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Background

`STAGE_DEPLOY_RUNBOOK.md` has been hardened to V1 and now records:

- explicit target stage host
- explicit Python 3.11 parent-check path
- explicit precheck
- explicit controlled validation candidate command
- explicit postcheck
- explicit rollback decision surface
- explicit non-goals and safety boundary

The current target stage host is:

- Provider / role: Vultr Project Anchor stage host
- Public IP: `45.76.190.109`
- Hostname: `vultr`
- Repo path: `/root/project-anchor`
- Backend compose path: `/root/project-anchor/anchor-backend`

The current parent-check path is:

```bash
PYTHON=python3.11 bash scripts/check_local_box_baseline.sh
```

## Authorization question

Should the project authorize the first controlled validation of the one-command stage deploy runbook?

## Decision

Authorization decision: YES.

The project may proceed to one controlled stage deploy validation task, using the hardened runbook and the boundaries below.

This authorization does not authorize real external request, live trading, credential changes, kill switch changes, or any production execution mode change.

## Authorized validation scope

The next validation task may authorize:

- SSH to the target stage host
- read-only precheck collection
- execution of the controlled deploy validation candidate command from `STAGE_DEPLOY_RUNBOOK.md`
- read-only postcheck collection
- rollback decision recording if validation fails

The controlled deploy validation candidate command is:

```bash
cd /root/project-anchor/anchor-backend
docker compose up -d --build
docker compose stop worker 2>/dev/null || true
sleep 2
docker compose up -d worker
```

This command is high-impact because it may rebuild or recreate backend containers and recycle the worker. It must be run only inside the next explicit validation task.

## Required precheck before execution

The next validation task must collect the runbook precheck before running the deploy command:

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

If the precheck shows an unexpected host, missing repo path, missing Python 3.11, missing Docker runtime visibility, or an unclear runtime state, the validation task must stop before deploy execution.

## Required postcheck after execution

If the deploy validation command is executed, the next validation task must collect:

```bash
cd /root/project-anchor
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker inspect anchor-backend-backend-1 --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}} StartedAt={{.State.StartedAt}}'
docker inspect anchor-backend-worker-1 --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}} StartedAt={{.State.StartedAt}}'
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/ops/state
PYTHON=python3.11 bash scripts/check_local_box_baseline.sh
bash scripts/check_go_live_rules.sh
git status -sb
```

## Hard boundaries

The validation task is not allowed to perform:

- credential changes
- `.env` changes
- kill switch changes
- new command creation
- real external request
- live trading
- production execution mode change
- unrelated package upgrades
- unrelated deploy changes
- manual recovery actions without explicit rollback decision

The following must remain true:

- Real external request: NOT AUTHORIZED
- Live trading: NO-GO
- Go-live: NO-GO

## Success criteria

The first controlled validation may be marked PASS only if all are true:

- target host identity confirmed
- repo path confirmed
- git revision and dirty state recorded
- Python 3.11 availability confirmed
- precheck completed
- deploy validation command executed without unhandled error
- backend status visible after validation
- worker status visible after validation
- `/health` returns OK after validation
- `/ops/state` is reachable after validation
- `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh` passes
- `bash scripts/check_go_live_rules.sh` passes
- rollback decision surface is not needed, or is explicitly recorded
- no credential change occurred
- no kill switch change occurred unless separately authorized and recorded
- no new command was created
- real external request remains NOT AUTHORIZED
- live trading remains NO-GO

## Failure handling

If validation fails:

1. Stop.
2. Do not improvise recovery.
3. Collect failure point and visible runtime state.
4. Record rollback decision surface.
5. Do not create commands.
6. Do not change credentials.
7. Do not change kill switch.
8. Keep real external request NOT AUTHORIZED.
9. Keep live trading NO-GO.

Failure closeout must state:

```text
[One-command Deployment Validation Failure]
failure point:
backend status:
worker status:
health result:
ops state result:
baseline result:
go-live rules result:
rollback required: YES/NO
rollback action proposed:
operator approval present: YES/NO
real external request: NOT AUTHORIZED
live trading: NO-GO
```

## Final authorization result

- One-command deployment validation authorization: YES
- Validation execution performed by this document: NO
- Next valid task: One-command Deployment Runbook First Controlled Validation
- Real external request authorized: NO
- Live trading: NO-GO

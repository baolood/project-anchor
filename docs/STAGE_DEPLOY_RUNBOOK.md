# Stage deploy runbook — hardened V1

**Status:** first controlled validation completed on 2026-05-31; retained as active validated baseline for future stage deploy runs.
**GO_LIVE_CHECKLIST link:** §4 Week 2 — `One-command deployment runbook validated`.
**Owner:** baolood.

## 0) Current decision

This runbook has now been exercised once through a first controlled validation on the stage host.
This document does **not** authorize real external request, live trading, or any production execution mode change.

Current boundary:

- Deploy authorized by this document: NO
- SSH authorized by this document: NO
- Backend restart authorized by this document: NO
- Worker restart authorized by this document: NO
- Docker rebuild authorized by this document: NO
- Credential change authorized: NO
- Kill switch change authorized: NO
- New command creation authorized: NO
- Real external request authorized: NO
- Live trading: NO-GO

## 1) Target stage host

Current stage host facts:

- Provider / role: Vultr Project Anchor stage host
- Public IP: `45.76.190.109`
- Hostname: `vultr`
- OS family: Ubuntu Linux x86_64
- Repo path: `/root/project-anchor`
- Backend compose path: `/root/project-anchor/anchor-backend`

Known host context:

- Stage checkout has been synced to current `main` as of the parity closeout.
- Host-local dirty file may exist:
  - `anchor-backend/docker-compose.override.yml`
- This dirty file must not be overwritten by the deploy validation unless separately authorized.
- First controlled validation executed against host checkout revision `deda43e`; the known dirty file remained `anchor-backend/docker-compose.override.yml` before and after validation.

## 2) Python path

Parent baseline / smoke checks must use explicit Python 3.11:

```bash
PYTHON=python3.11 bash scripts/check_local_box_baseline.sh
```

Do not rely on default `python3`.

Known intended state:

- `python3` may remain `3.10.12`
- `python3.11` must exist
- parent checks use `PYTHON=python3.11`

## 3) First validation precheck

Before any deploy validation is authorized, collect these read-only checks on the stage host:

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

Precheck must confirm:

- host identity visible
- repo path visible
- git revision visible
- dirty state known
- `python3.11` available
- Docker runtime state visible
- backend health reachable or failure recorded
- ops state reachable or failure recorded
- kill switch state visible if `/ops/state` is reachable
- no runtime mutation performed during precheck

## 4) Controlled validation candidate command

The deploy validation command candidate is:

```bash
cd /root/project-anchor/anchor-backend
docker compose up -d --build
docker compose stop worker 2>/dev/null || true
sleep 2
docker compose up -d worker
```

This command is intentionally high-impact because it may rebuild/recreate backend containers and recycle the worker.

It must not be executed until a separate validation task explicitly authorizes:

- SSH
- deploy validation
- backend / worker container changes
- rollback observation
- postcheck collection

## 5) Post-deploy validation

After an authorized deploy validation, collect:

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

Postcheck must record:

- backend running
- worker running
- backend health OK
- ops state reachable
- kill switch state unchanged or explicitly recorded
- worker heartbeat visible
- parent baseline PASS under `PYTHON=python3.11`
- go-live rules PASS
- git dirty state still known
- no new command created
- no real external request authorized
- live trading remains NO-GO

## 6) Acceptance criteria

One-command deployment runbook validated may be marked DONE only if all are true:

- stage host is explicit
- precheck completed
- deploy validation command completed or failure was cleanly recorded
- postcheck completed
- `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh` PASS
- `bash scripts/check_go_live_rules.sh` PASS
- backend health OK
- worker state visible
- rollback decision surface recorded
- no credential changes
- no kill switch changes unless separately authorized and recorded
- no new command creation
- real external request remains NOT AUTHORIZED
- live trading remains NO-GO

## 7) Rollback decision surface

If the deploy validation fails, do not improvise.

Record:

```text
[Stage Deploy Validation Rollback Decision]
failure point:
backend status:
worker status:
health result:
ops state result:
baseline result:
go-live rules result:
rollback required: YES/NO
rollback action proposed:
runtime restart required: YES/NO
operator approval present: YES/NO
real external request: NOT AUTHORIZED
live trading: NO-GO
```

Rollback action must be separately authorized unless the failure is limited to collecting logs or read-only checks.

## 8) Duration baseline

Observed during first authorized validation on 2026-05-31:

| Step | Started UTC | Finished UTC | Wall seconds | Result | Notes |
|------|-------------|--------------|--------------|--------|-------|
| precheck | 2026-05-31T14:48:30+00:00 | 2026-05-31T14:48:30+00:00 | snapshot | PASS | Host identity, repo path, Python 3.11, Docker state, `/health`, and `/ops/state` all visible before deploy execution. |
| deploy command | 2026-05-31T14:48:30+00:00 | 2026-05-31T14:49:17+00:00 | ~47 | PASS | Backend image rebuilt, backend container recreated, worker recycled and started. Finish marker based on host-side `StartedAt` for worker. |
| postcheck | 2026-05-31T14:49:40+00:00 | 2026-05-31T14:49:40+00:00 | snapshot | PASS | Backend and worker visible; `/health` OK; `/ops/state` reachable; worker heartbeat fresh. |
| parent baseline | 2026-05-31T14:49:40+00:00 | 2026-05-31T14:49:40+00:00 | logged in evidence | PASS | `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh` returned `BASELINE_RC=0`. |
| go-live rules | 2026-05-31T14:49:40+00:00 | 2026-05-31T14:49:40+00:00 | logged in evidence | PASS | `bash scripts/check_go_live_rules.sh` returned `GO_LIVE_RULES_RC=0`. |

## 9) First validation closeout template

```text
[One-command Deployment Runbook Validation Closeout]
target host:
- host:
- repo path:
- git revision:
- git dirty state:
precheck:
- PASS/FAIL
deploy command:
- executed: YES/NO
- result: PASS/FAIL
postcheck:
- docker status collected: YES/NO
- /health: PASS/FAIL
- /ops/state: PASS/FAIL
- PYTHON=python3.11 baseline: PASS/FAIL
- go-live rules: PASS/FAIL
boundary:
- credential changed: NO
- kill switch changed: NO unless explicitly recorded
- new command created: NO
- real external request: NOT AUTHORIZED
- live trading: NO-GO
decision:
- one-command deployment runbook validated: YES/NO
```

## 10) Final status of this document

- Stage host explicit: YES
- Python 3.11 path explicit: YES
- Precheck explicit: YES
- Deploy command explicit: YES
- Postcheck explicit: YES
- Rollback decision surface explicit: YES
- First real validation performed by this document: YES
- First validation result: PASS
- Validation evidence bundle: `docs/ONE_COMMAND_DEPLOYMENT_RUNBOOK_FIRST_CONTROLLED_VALIDATION_CLOSEOUT_V1.md`
- Real external request authorized: NO
- Live trading: NO-GO

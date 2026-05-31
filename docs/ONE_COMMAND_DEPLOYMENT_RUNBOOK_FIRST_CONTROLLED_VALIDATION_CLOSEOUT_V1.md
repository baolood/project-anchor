# One-command Deployment Runbook First Controlled Validation Closeout V1

## Scope

- Validation type: first controlled stage deploy validation
- Target host: Vultr Project Anchor stage host
- Public IP: `45.76.190.109`
- Hostname: `vultr`
- Repo path: `/root/project-anchor`
- Backend compose path: `/root/project-anchor/anchor-backend`
- Real external request authorized: NO
- Live trading: NO-GO

## Precheck

- Collection timestamp: `2026-05-31T14:48:30+00:00`
- Host identity: PASS
- Repo path visible: PASS
- Git revision recorded: `deda43e`
- Git dirty state recorded: `anchor-backend/docker-compose.override.yml`
- `python3` visible: `Python 3.10.12`
- `python3.11` visible: `Python 3.11.0rc1`
- Docker runtime visible: PASS
- `/health` reachable before deploy: PASS (`{"ok":true}`)
- `/ops/state` reachable before deploy: PASS
- Kill switch before deploy: `false`
- Worker heartbeat before deploy: fresh

## Controlled deploy command

Executed command:

```bash
cd /root/project-anchor/anchor-backend
docker compose up -d --build
docker compose stop worker 2>/dev/null || true
sleep 2
docker compose up -d worker
```

Result:

- Executed: YES
- Deploy command result: PASS
- Backend image rebuilt: YES
- Worker image rebuilt: YES
- Backend container recreated: YES
- Worker container recreated: YES
- Backend started after recreate: YES
- Worker started after recycle: YES

Observed host-side start markers:

- Backend `StartedAt`: `2026-05-31T14:49:04.053020938Z`
- Worker `StartedAt`: `2026-05-31T14:49:17.073970534Z`

## Postcheck

- Postcheck snapshot time: `2026-05-31T14:49:40+00:00`
- Backend visible after validation: YES
- Worker visible after validation: YES
- Backend status after validation: `Up`
- Worker status after validation: `Up`
- `/health` after validation: PASS (`{"ok":true}`)
- `/ops/state` after validation: PASS
- Kill switch after validation: `false`
- Worker heartbeat after validation: fresh at `2026-05-31T14:49:17.606405Z`
- `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh`: PASS (`BASELINE_RC=0`)
- `bash scripts/check_go_live_rules.sh`: PASS (`GO_LIVE_RULES_RC=0`)
- Git dirty state after validation: `anchor-backend/docker-compose.override.yml`

## Boundary result

- Credential changed: NO
- `.env` changed: NO
- Kill switch changed: NO
- New command created: NO
- Real external request: NOT AUTHORIZED
- Live trading: NO-GO
- Runtime mutation outside controlled deploy validation: NO

## Interpretation

This validation proves:

- the hardened stage deploy runbook can be executed once on the explicit target host
- the controlled deploy command can rebuild/recreate backend containers and recycle the worker without immediate postcheck failure
- the parent baseline can still pass under `PYTHON=python3.11` after the controlled deploy validation
- go-live rules remain PASS after the controlled deploy validation

This validation does **not** prove:

- real external request readiness
- live trading readiness
- production execution mode readiness

## Final decision

- One-command deployment runbook validated: YES
- Validation bounded to this controlled stage deploy run: YES
- Rollback decision surface needed: NO
- Real external request authorized: NO
- Live trading: NO-GO

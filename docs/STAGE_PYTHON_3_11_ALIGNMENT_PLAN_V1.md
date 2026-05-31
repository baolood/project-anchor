# Stage Python 3.11 Alignment Plan V1

## Status

- Document type: execution plan only
- Host change authorized: NO
- SSH authorized in this plan step: NO
- Python install authorized in this plan step: NO
- Runtime switch authorized in this plan step: NO
- Container restart authorized in this plan step: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Background

`STAGE_PYTHON_MINOR_PARITY_DECISION_V1` fixed the current stage-host Python decision:

- Target stage host: `45.76.190.109`
- Hostname: `vultr`
- Platform: `Linux x86_64`
- Current stage host parent Python: `3.10.12`
- Local / CI parent baseline target: Python `3.11.x`
- Decision: do not accept Python `3.10.12` as the long-term intentional delta
- Preferred path: align the stage host parent Python path to Python `3.11`

This plan defines the minimum safe path for that future host change. It does not perform the change.

## Goal

Align the stage host parent Python runtime used for parent smokes / baseline checks to Python `3.11.x`, without changing trading behavior, runtime mode, credentials, kill switch state, or deployment posture.

## Non-goals

This plan does not authorize:

- real external request
- live trading
- credential changes
- `.env` changes
- kill switch changes
- worker restart
- backend restart
- Docker image rebuild
- deploy
- `git pull`
- package upgrades unrelated to Python 3.11 availability
- changing production execution mode

## Proposed alignment path

Preferred path for the future implementation step:

1. Confirm current host state with read-only checks.
2. Install or activate a system-level Python `3.11` binary without changing the default `python3` symlink.
3. Verify `python3.11 --version`.
4. Run parent baseline/smoke checks using an explicit `PYTHON=python3.11` override.
5. Keep runtime containers untouched unless a later task explicitly authorizes a separate runtime deployment.
6. Record validation evidence.
7. Only after validation, update parity status.

The future implementation should prefer explicit invocation:

```bash
PYTHON=python3.11 bash scripts/check_local_box_baseline.sh
```

It should not rely on replacing the host default `python3`.

## Expected future read-only precheck

Before any host change, collect:

```bash
hostname
date -Is
cd /root/project-anchor || cd /opt/project-anchor/project-anchor
pwd
git rev-parse --short HEAD
git status -sb
python3 --version || true
python3.11 --version || true
which python3 || true
which python3.11 || true
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

## Expected future change boundary

Allowed in the future implementation step, only after explicit authorization:

- install or activate Python 3.11
- verify `python3.11`
- run explicit Python 3.11 validation commands

Not allowed in that implementation step unless separately authorized:

- `git pull`
- deploy
- Docker restart
- backend restart
- worker restart
- credential changes
- kill switch changes
- new command creation
- real external request
- live trading

## Validation requirements

A future implementation may be considered successful only if all are true:

- `python3.11 --version` returns Python `3.11.x`
- parent baseline runs with explicit Python 3.11 and passes
- `scripts/check_go_live_rules.sh` passes
- `git status -sb` is either clean or has only explicitly documented expected host-local drift
- no backend or worker restart was performed
- no new command was created
- real external request remains `NOT AUTHORIZED`
- live trading remains `NO-GO`

## Acceptance template

```text
[Stage Python 3.11 Alignment Validation]
host:
- hostname:
- repo path:
- git revision:
- git status:
python:
- python3 --version:
- python3.11 --version:
- python3.11 path:
validation:
- PYTHON=python3.11 bash scripts/check_local_box_baseline.sh: PASS/FAIL
- bash scripts/check_go_live_rules.sh: PASS/FAIL
boundary:
- git pull performed: NO
- deploy performed: NO
- backend restarted: NO
- worker restarted: NO
- credential changed: NO
- kill switch changed: NO
- new command created: NO
- real external request: NOT AUTHORIZED
- live trading: NO-GO
decision:
- stage Python 3.11 alignment complete: YES/NO
```

## Rollback plan

If Python 3.11 activation or install causes issues in a future implementation:

1. Stop validation.
2. Do not restart runtime services.
3. Do not change credentials or kill switch.
4. Restore the previous Python invocation path for local checks.
5. If a package was installed and must be removed, remove only that Python 3.11 package through the same package manager used to install it.
6. Re-run read-only host state checks.
7. Record stage Python alignment as incomplete.

Rollback decision template:

```text
[Stage Python 3.11 Alignment Rollback]
rollback required: YES
reason:
action taken:
python3.11 available after rollback: YES/NO
runtime restarted: NO
real external request: NOT AUTHORIZED
live trading: NO-GO
stage Python 3.11 alignment complete: NO
```

## Final decision

- Stage Python 3.11 alignment plan ready: YES
- Host change performed by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

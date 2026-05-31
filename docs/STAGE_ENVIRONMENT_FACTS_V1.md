# STAGE_ENVIRONMENT_FACTS_V1

## Stage Host

- STAGE_HOST_URL: `45.76.190.109`
- STAGE_DEPLOY_TARGET: `docker compose on single VM`
- STAGE_OWNER: `baolood`
- STAGE_DATA_SCOPE: `synthetic data only / empty database initialization`
- STAGE_AVAILABLE_FROM: `2026-05-08`
- HOSTNAME: `vultr`
- STAGE_RUNTIME_OS_ARCH: `Linux x86_64`
- STAGE_PARENT_PYTHON_DEFAULT: `Python 3.10.12`
- STAGE_PARENT_PYTHON_VALIDATED: `Python 3.11.0rc1` via explicit `python3.11`
- STAGE_PARENT_PYTHONPATH_DEFAULT: `<unset>`
- STAGE_PARENT_DB_PATH: `/root/project-anchor/anchor.db`
- STAGE_SQLITE_VERSION: `3.37.2`

## Validation Evidence

Validated on real stage host:

- SSH login: PASS
- Docker: PASS
- Docker Compose: PASS
- Git clone: PASS
- `./scripts/check_local_box_baseline.sh`: PASS
- `PYTHONPATH=. python3 -c "import local_box.control.server"`: PASS
- Read-only parity fact collection (`hostname`, `uname -sm`, `python3 --version`, parent DB path, SQLite version): PASS on `2026-05-31T09:01:57+00:00`
- Stage checkout sync to current `main`: PASS on `2026-05-31T11:11:40+00:00`
- Explicit parent validation with `PYTHON=python3.11`: PASS on `2026-05-31T11:12:01+00:00`

## Current Boundary

- No deployment performed
- No services started
- No production secrets configured
- No external traffic enabled
- Stage target is now concrete enough to use as the shared Week 2-6 reference host.
- Host default `python3` remains `3.10.12`, but parent baseline parity is validated through explicit `python3.11` invocation.
- No backend restart, worker restart, deploy, or real external request was performed during Python 3.11 alignment validation.

# STAGE_ENVIRONMENT_FACTS_V1

## Stage Host

- STAGE_HOST_URL: `45.76.190.109`
- STAGE_DEPLOY_TARGET: `docker compose on single VM`
- STAGE_OWNER: `baolood`
- STAGE_DATA_SCOPE: `synthetic data only / empty database initialization`
- STAGE_AVAILABLE_FROM: `2026-05-08`
- HOSTNAME: `vultr`
- STAGE_RUNTIME_OS_ARCH: `Linux x86_64`
- STAGE_PARENT_PYTHON: `Python 3.10.12`
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

## Current Boundary

- No deployment performed
- No services started
- No production secrets configured
- No external traffic enabled
- Stage target is now concrete enough to use as the shared Week 2-6 reference host, but parent Python minor parity against CI/local still needs explicit follow-up.

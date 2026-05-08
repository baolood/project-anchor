# STAGE_ENVIRONMENT_FACTS_V1

## Stage Host

- STAGE_HOST_URL: `45.76.190.109`
- STAGE_DEPLOY_TARGET: `docker compose on single VM`
- STAGE_OWNER: `baolood`
- STAGE_DATA_SCOPE: `synthetic data only / empty database initialization`
- STAGE_AVAILABLE_FROM: `2026-05-08`
- HOSTNAME: `vultr`

## Validation Evidence

Validated on real stage host:

- SSH login: PASS
- Docker: PASS
- Docker Compose: PASS
- Git clone: PASS
- `./scripts/check_local_box_baseline.sh`: PASS
- `PYTHONPATH=. python3 -c "import local_box.control.server"`: PASS

## Current Boundary

- No deployment performed
- No services started
- No production secrets configured
- No external traffic enabled

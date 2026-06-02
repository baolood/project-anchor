# G3 Backup Artifact Scratch Target Preflight V1

## Status

- Preflight type: bounded restore drill preconditions only
- backup artifact created or verified: YES
- scratch target implemented: YES
- actual restore drill executed: NO
- production overwrite authorized: NO
- RPO measured: NO
- RTO measured: NO
- G3 ready for DONE: NO
- live trading: NO-GO
- real external request: NOT AUTHORIZED

## Host commands executed

The following bounded host-side actions were performed:

1. recorded git state from `/root/project-anchor`
2. recorded active postgres container identity
3. listed visible databases before scratch target creation
4. created a bounded backup artifact from database `anchor`
5. recorded artifact path, size, and sha256
6. created scratch database target `anchor_restore_drill_scratch`
7. listed visible databases after scratch target creation

No restore command was executed.

## Preflight runtime evidence

- host: `vultr`
- repo: `/root/project-anchor`
- revision: `0fe4a86`
- git state:
  - `## main...origin/main`
  - dirty file: `anchor-backend/docker-compose.override.yml`
  - untracked file: `TELEGRAM_ALERT_ACCEPTANCE_20260601-143247.txt`
- active postgres container: `anchor-backend-postgres-1`
- active data volume:
  `anchor-backend_pgdata -> /var/lib/postgresql/data`
- visible databases before scratch target creation:
  - `anchor`
  - `postgres`
  - `template0`
  - `template1`

## Backup artifact

- created/verified: YES
- path:
  `/root/project-anchor/artifacts/g3-restore-drill/anchor_g3_pre_restore_20260602T011223Z.dump`
- size: `3452055`
- sha256:
  `03588b00fe0a6e25b27573bed139b44eb4dc0d219a1e9b672a144dbcf6a4862b`
- outside postgres data volume: YES

## Scratch target

- implemented: YES
- target name: `anchor_restore_drill_scratch`
- target != `anchor`: YES
- implementation action: `CREATED`
- visible databases after scratch target creation:
  - `anchor`
  - `anchor_restore_drill_scratch`
  - `postgres`
  - `template0`
  - `template1`

## Forbidden actions performed

- restore executed: NO
- production overwrite: NO
- live trading: NO-GO
- external request: NOT AUTHORIZED
- env/docker/backend/worker/risk changed: NO

## Interpretation

This preflight proves that the next G3 step can move past “missing artifact /
missing scratch target” blockers.

It does **not** prove restore correctness, does **not** satisfy G3, and does
**not** authorize production overwrite.

## Final preflight result

- backup artifact created/verified: YES
- scratch target implemented: YES
- actual restore drill executed: NO
- production overwrite authorized: NO
- RPO measured: NO
- RTO measured: NO
- G3 ready for DONE: NO

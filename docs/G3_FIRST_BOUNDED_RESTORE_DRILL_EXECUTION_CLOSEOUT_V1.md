# G3 First Bounded Restore Drill Execution Closeout V1

## Status

- Closeout type: first bounded restore drill execution
- Restore drill result: PASS
- Restore drill row moved to DONE by this closeout: YES
- G3 moved to DONE by this closeout: YES
- Actual restore drill executed: YES
- Production overwrite authorized: NO
- Production data modified: NO
- RPO measured: YES
- RTO measured: YES
- Real external request authorized: NO
- Live trading: NO-GO

## Runtime evidence summary

Observed runtime context at drill start:

- host: `vultr`
- repo: `/root/project-anchor`
- revision: `0fe4a86`
- active postgres container: `anchor-backend-postgres-1`
- active production database: `anchor`
- scratch target: `anchor_restore_drill_scratch`
- production overwrite path used: NO

## Backup artifact used

- path:
  `/root/project-anchor/artifacts/g3-restore-drill/anchor_g3_pre_restore_20260602T011223Z.dump`
- exists: YES
- size: `3452055`
- sha256:
  `03588b00fe0a6e25b27573bed139b44eb4dc0d219a1e9b672a144dbcf6a4862b`
- outside postgres data volume: YES

## Scratch target used

- target name: `anchor_restore_drill_scratch`
- target != `anchor`: YES
- target created before drill: YES
- visible production DB retained: YES

## Restore execution summary

Bounded execution path:

1. verified source DB identity = `anchor`
2. verified target DB identity = `anchor_restore_drill_scratch`
3. verified target != source
4. restored dump into scratch target only
5. performed post-restore sanity verification
6. did not overwrite `anchor`

## Sanity verification

Stable/core table checks matched exactly:

- `commands_domain`: `129` vs `129`
- `ops_state`: `2` vs `2`
- `risk_state`: `1` vs `1`

Mutable event table observation:

- production `domain_events` count at restore-check time:
  `289737`
- restored scratch `domain_events` count:
  `289715`
- production latest `domain_events.created_at`:
  `2026-06-02 01:23:20.926496+00`
- scratch latest `domain_events.created_at`:
  `2026-06-02 01:12:18.58169+00`

Interpretation:

- the scratch restore reflects the backup point-in-time
- production continued to receive new events after the dump was created
- the observed delta is therefore interpreted as expected RPO window behavior,
  not restore corruption

## RPO / RTO result

- observed RPO seconds: `645`
- RPO target from **`docs/BACKUP_AND_RECOVERY.md`**:
  `<= 3600` seconds for DB-BACKEND
- RPO result: PASS

- observed RTO seconds: `4`
- RTO target from **`docs/BACKUP_AND_RECOVERY.md`**:
  `<= 14400` seconds
- RTO result: PASS

## Boundaries preserved

The following remained true during this drill:

- no restore was executed against `anchor`
- no production overwrite occurred
- no secrets were printed
- no live trading was enabled
- no real external request was authorized

## Week 4 / G3 result

The following may now be judged complete:

- **`Restore drill (table-level + full restore)`**: DONE for the current
  bounded first official G3 drill scope
- **`G3 — Backup/restore drill within RPO/RTO`**: DONE

This closeout does **not** by itself mark:

- **`Backup strategy implemented`** as DONE

That row still depends on schedule / retention / verification policy beyond the
single restore drill.

## Final closeout result

- first bounded restore drill execution: PASS
- bounded restore target used correctly: YES
- backup artifact evidence present: YES
- actual restore drill executed: YES
- production overwrite authorized: NO
- RPO measured: YES
- RTO measured: YES
- G3 ready for DONE: YES

# G3 Backup Restore Drill Inventory V1

## Current G3 status

- G3 — Backup/restore drill within RPO/RTO: NOT_DONE
- actual restore drill executed: NO
- production data modified: NO
- live trading: NO-GO
- real external request: NOT AUTHORIZED

## Purpose

This inventory defines the first bounded scope, evidence expectations, and
non-negotiable safety boundaries for the future G3 backup/restore drill.

It does **not** execute a restore, does **not** modify production data, and
does **not** prove recovery capability by itself.

## Backup / restore scope inventory

### Database backup target

- primary current database recovery scope:
  - **DB-PARENT** logical/local-box database path
  - **DB-BACKEND** backend database target described in
    **`docs/BACKUP_AND_RECOVERY.md`**
- backup artifact class:
  - logical dump, vendor snapshot, or equivalent restorable artifact
- accepted inventory outcome in this phase:
  - recovery targets named
  - backup artifact class named
  - restore target bounded

### Restore target

- restore must be executed only into a bounded non-production target
- accepted restore target classes:
  - disposable restore sandbox
  - isolated test database
  - newly created scratch volume / instance
- explicitly not accepted:
  - overwrite of active production data
  - restore into live trading path
  - restore into any target that can silently affect real external execution

### Evidence required

- backup artifact identifier or path
- backup artifact creation timestamp
- restore target identifier
- exact restore command or vendor flow record
- post-restore read-only verification output
- elapsed execution timing

### RPO evidence placeholder

- source backup timestamp:
- restore point timestamp:
- calculated data-loss window:
- target RPO:
- RPO result: PASS/FAIL

### RTO evidence placeholder

- restore start timestamp:
- restore verification complete timestamp:
- total wall time:
- target RTO:
- RTO result: PASS/FAIL

### Rollback / abort condition

Abort or roll back the future drill if any of the following is true:

- restore target is not clearly non-production
- backup artifact cannot be identified unambiguously
- restore command would overwrite an active production target
- restore verification would require secret disclosure
- restored application health/read-only verification fails
- elapsed execution exceeds agreed stop boundary without safe pause

## Minimum drill boundary

- restore must be performed only into a bounded non-production target
- no live production overwrite
- no trading / external execution
- no secret exposure
- no irreversible operation accepted without explicit rollback path

## Acceptance evidence placeholders

- backup artifact present: YES/NO
- restore command recorded: YES/NO
- restore target verified: YES/NO
- app health/read-only verification after restore: YES/NO
- elapsed time recorded: YES/NO
- RPO result recorded: YES/NO
- RTO result recorded: YES/NO

## Explicitly not accepted

- screenshots alone
- claims without command output
- production mutation
- external request
- live trading

## Relationship to existing Week 4 documents

This inventory pairs with:

- **`docs/BACKUP_AND_RECOVERY.md`**
- **`docs/RESTORE_DRILL_RUNBOOK.md`**
- **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 4 and §5 G3

This inventory means:

- inventory prepared only: YES
- actual restore drill executed: NO
- G3 ready to move to DONE: NO

## Final inventory result

- G3 inventory prepared: YES
- G3 restore execution completed: NO
- production data modified: NO
- real external request authorized: NO
- live trading: NO-GO

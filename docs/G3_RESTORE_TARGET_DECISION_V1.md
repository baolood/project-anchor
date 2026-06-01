# G3 Restore Target Decision V1

## Status

- Decision type: bounded restore target decision only
- Restore target decision made: YES
- Actual restore drill executed by this document: NO
- Production data modified by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Current context

Week 4 recovery work now has:

- inventory prepared:
  **`docs/G3_BACKUP_RESTORE_DRILL_INVENTORY_V1.md`**
- backup strategy draft:
  **`docs/BACKUP_AND_RECOVERY.md`**
- restore drill draft:
  **`docs/RESTORE_DRILL_RUNBOOK.md`**

What is still missing is a concrete bounded restore target that can be used for
the first G3 drill without risking production overwrite.

## Decision question

What restore target is acceptable for the first backup/restore drill used to
support Week 4 and hard gate **G3**?

## Decision

Authorization decision: use a **bounded non-production restore target only**.

Accepted first restore target:

- a disposable, operator-created restore sandbox on the stage host
- isolated from the active production-facing runtime
- not attached to the live backend/worker containers
- not capable of triggering trading or real external execution

Rejected restore target classes:

- active production database
- any database/volume currently serving the live stage runtime
- any target that shares write-path side effects with the live trading path
- any target whose overwrite would require trust in manual memory rather than
  explicit identifier verification

## Accepted target shape

The first G3 restore must land in a target with all of the following:

1. explicit identifier before restore
2. explicit proof it is non-production
3. disposable lifetime or clean rollback path
4. read-only verification possible after restore
5. no dependency on live trading or real external execution

Examples of acceptable target classes:

- isolated scratch database created only for the drill
- disposable restore volume mounted only into a sandbox container
- temporary local DB file copy used strictly for validation

This decision deliberately does **not** choose the exact command yet. That must
be recorded in the future execution plan once the concrete backend storage mode
and operator path are confirmed.

## Minimum verification before future restore execution

Before the actual drill starts, the operator must be able to record:

- restore target name / path / identifier
- proof the target is non-production
- proof the target is not currently mounted by the active backend/worker path
- rollback / disposal step for the target

If any one of those is missing, the drill must stop before restore execution.

## Evidence expectation

The future G3 evidence bundle must include:

- chosen restore target identifier
- operator statement of why the target is non-production
- restore command or vendor flow
- post-restore app/read-only verification
- elapsed timing
- RPO/RTO result

## What this decision does not do

This decision does **not**:

- execute a restore
- prove backup integrity
- prove restore correctness
- choose final restore command syntax
- modify production data
- authorize real external request
- authorize live trading

## Week 4 / G3 result after this decision

- restore target bounded: YES
- actual restore drill executed: NO
- G3 ready for DONE: NO
- next valid task: bounded restore execution plan or restore target implementation review

## Final decision result

- bounded restore target decision: PASS
- production-safe target class chosen: YES
- production overwrite authorized: NO
- real external request authorized: NO
- live trading: NO-GO

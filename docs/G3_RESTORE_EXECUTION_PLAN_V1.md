# G3 Restore Execution Plan V1

## Current G3 state

- G3 — Backup/restore drill within RPO/RTO: NOT_DONE
- bounded restore target decision: PASS
- restore target: bounded non-production target only
- actual restore drill executed: NO
- production overwrite authorized: NO
- live trading: NO-GO
- real external request: NOT AUTHORIZED
- go-live: NO-GO

## Purpose

This document defines the first bounded restore drill procedure for G3.

It does **not** execute a restore. It does **not** modify production data. It
does **not** authorize production overwrite, live trading, or external
requests.

## First restore drill boundary

- restore must run only against a bounded non-production target
- production database overwrite is forbidden
- live trading remains NO-GO
- external request remains NOT AUTHORIZED
- secrets must not be printed
- no destructive cleanup without explicit command evidence

## Planned restore target

- use the already-decided bounded non-production target from
  **`docs/G3_RESTORE_TARGET_DECISION_V1.md`**
- this plan does **not** create or mutate the target
- the target must be explicitly verified before future execution
- future execution evidence must show:
  - target identifier
  - non-production proof
  - isolation from the active backend/worker runtime

## Planned restore type

Safest first official G3 drill shape:

- bounded database-level restore into a non-production target

Reasoning:

- it validates recoverability without production overwrite
- it avoids depending on more granular table-level assumptions as the first
  official G3 proof
- it keeps the first drill centered on whole-target restoration, timing, and
  read-only verification

This plan does **not** reject future table-level drills. It only chooses the
safest first official G3 execution shape.

## Planned execution sequence

The future bounded restore drill should proceed in this order:

1. record pre-drill production identity
2. record non-production target identity
3. verify backup artifact presence
4. declare restore start timestamp
5. execute bounded restore into the non-production target
6. record restore command output
7. record restore completion timestamp
8. run post-restore database/table sanity check
9. run read-only app or query verification
10. measure RPO
11. measure RTO
12. record final PASS/FAIL verdict

The drill must stop at any stop condition below before progressing further.

## Required future command evidence

The future evidence bundle must include placeholders filled with exact outputs:

- pre-drill production identity check
- non-production target identity check
- backup artifact presence check
- restore command output
- restore elapsed time
- post-restore database/table sanity check
- read-only app or query verification
- RPO measurement
- RTO measurement
- final PASS/FAIL verdict

## Mandatory stop conditions

The future drill must stop immediately if:

- target identity is unclear
- target points to production
- command would overwrite production
- backup artifact is missing
- secrets would be printed
- restore command is ambiguous
- any trading/external execution path is involved
- rollback/cleanup path is unclear

## Failure interpretation

The future drill must be recorded as FAIL if any of the following is true:

- restore command does not complete
- restore target cannot be verified as non-production
- post-restore sanity checks fail
- read-only application/query verification fails
- RPO target is missed
- RTO target is missed
- production overwrite occurs

Failure in the future drill must **not** be rewritten as “inventory complete”
or “plan complete.” Execution failure is still a failed G3 drill.

## G3 DONE criteria

G3 can only be marked DONE after:

- actual bounded restore execution completed
- RPO measured
- RTO measured
- restore target verified as non-production
- post-restore verification passed
- evidence captured in docs
- no production overwrite occurred

## Explicit non-claims

- This plan does not prove restore works
- This plan does not satisfy G3
- This plan does not authorize production overwrite
- This plan does not authorize live trading
- This plan does not authorize external requests

## Final plan result

- restore execution plan prepared: YES
- actual restore drill executed: NO
- production overwrite authorized: NO
- RPO/RTO measured: NO
- G3 ready for DONE: NO
- real external request authorized: NO
- live trading: NO-GO

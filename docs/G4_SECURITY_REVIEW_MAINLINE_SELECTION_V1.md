# G4 Security Review Mainline Selection V1

## 1) Current fixed completed hard gates

- `G1 — Deployment and rollback drills pass`: DONE
- `G2 — P0/P1 alerting verified`: DONE
- `G3 — Backup/restore drill within RPO/RTO`: DONE

## 2) Still-forbidden boundaries

- go-live: NO-GO
- real external request: NOT AUTHORIZED
- live trading: NO-GO
- production overwrite: NO

## 3) G4-related remaining inventory

Current G4 hard gate:

- `G4 — Security review complete (secrets + permissions + vuln baseline)`:
  NOT_DONE

Current Week 5-6 supporting rows directly tied to G4:

1. `Secret management and key rotation policy` — IN_PROGRESS
2. `Permission minimization and audit` — IN_PROGRESS

The current checklist excerpt reviewed for this selection does not yet show a
completed vuln-baseline closeout artifact, so the hard gate remains blocked at
least on secrets and permissions, and possibly on vulnerability baseline
evidence as well.

## 4) Next selected G4 mainline

Selected next single mainline:

- `Secret management and key rotation policy`

Selected item status:

- NOT_DONE

## 5) Why this is next

This is the highest-priority next G4 line because:

- it appears first in the Week 5-6 security checklist order
- the G4 hard-gate label explicitly begins with `secrets`
- the existing draft already names two missing evidence classes:
  - complete inventory
  - one tested rotation rehearsal

What evidence is still missing:

- a completed secret inventory
- a recorded no-plaintext verification result
- one rehearsed rotation procedure with evidence

What must not be done yet:

- do not mark `G4` DONE
- do not mark `Secret management and key rotation policy` DONE
- do not start runtime secret rotation without a narrower review / plan
- do not authorize go-live, live trading, or real external requests

## 6) Next task boundary

Next task type:

- docs-only

Next task name:

- `G4 Secret Inventory And Rotation Rehearsal Readiness Review V1`

Allowed files:

- `docs/G4_SECRET_INVENTORY_ROTATION_REHEARSAL_READINESS_REVIEW_V1.md`
- `docs/GO_LIVE_CHECKLIST.md`

Forbidden files/actions:

- `anchor-backend/**`
- `anchor-console/**`
- `docker-compose*`
- `migrations/**`
- `scripts/**`
- `.github/**`
- any env files
- any runtime config
- any generated runtime artifact
- any real secret rotation
- any host secret mutation

Validation commands:

- `git diff --check`
- `grep -n "Secret management and key rotation policy" docs/GO_LIVE_CHECKLIST.md`
- `grep -n "Selected next single mainline:" docs/G4_SECURITY_REVIEW_MAINLINE_SELECTION_V1.md`
- `grep -n "Secret management and key rotation policy" docs/G4_SECURITY_REVIEW_MAINLINE_SELECTION_V1.md`
- `git status --short`

Acceptance criteria:

- the next task reads the existing security drafts only
- the next task determines whether the secret inventory and rotation rehearsal
  path are sufficiently specified to proceed safely
- the next task does not rotate any real secret
- the next task preserves:
  - go-live: NO-GO
  - live trading: NO-GO
  - real external request: NOT AUTHORIZED

Rollback method:

- if the next task is incorrect before merge:
  - `git restore docs/G4_SECRET_INVENTORY_ROTATION_REHEARSAL_READINESS_REVIEW_V1.md docs/GO_LIVE_CHECKLIST.md`
- if merged and later found incorrect:
  - `git revert <commit>`

## 7) Explicit non-claims

- This selection does not authorize go-live.
- This selection does not authorize live trading.
- This selection does not authorize real external requests.
- This selection does not complete `G4`.
- This selection does not modify runtime behavior.

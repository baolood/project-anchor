# G4 SEC-CI Rehearsal Execution Preflight V1

## 1) Preflight question

This preflight asks:

- can the project safely start the first real `SEC-CI` rehearsal now?

This preflight does not rotate a secret, does not create a secret, and does
not modify GitHub settings.

## 2) Current fixed gate state

- `G1 — Deployment and rollback drills pass`: DONE
- `G2 — P0/P1 alerting verified`: DONE
- `G3 — Backup/restore drill within RPO/RTO`: DONE
- `G4 — Security review complete (secrets + permissions + vuln baseline)`:
  NOT_DONE
- `Secret management and key rotation policy`: NOT_DONE
- go-live: NO-GO
- real external request: NOT AUTHORIZED
- live trading: NO-GO

## 3) Presence-only checks performed

### 3.1 Parent no-plaintext scan

Command family used:

```bash
git grep -nE 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|secret[_-]?key\s*=' -- ':!docs/' ':!RELEASE_NOTES.md' || true
```

Observed result:

- no scan hits returned

Preflight interpretation:

- `NO_PLAINTEXT_SCAN_RESULT=PASS`

### 3.2 Repository identity

- repo identity confirmed: `baolood/project-anchor`

### 3.3 Repository Actions secrets presence

Presence-only check result:

- repository Actions secrets total count: `0`

Interpretation:

- no repo-scoped Actions secret target is currently visible for `SEC-CI`

### 3.4 GitHub environments presence

Presence-only check result:

- environments total count: `0`

Interpretation:

- no environment-scoped secret target is currently visible for `SEC-CI`

## 4) Preflight decision

Decision:

- NOT_READY for real `SEC-CI` rehearsal execution

Why:

1. no-plaintext scan path is usable and currently PASS
2. but the `SEC-CI` storage target is not currently present/visible in the
   repository or environment scope
3. without a valid storage target, the rehearsal cannot satisfy:
   - replacement created
   - post-rotation verification
   - rollback path clarity

## 5) What this preflight proves

- no-plaintext scan path can be run: YES
- current parent no-plaintext scan returned no hits: YES
- repo secret storage target for `SEC-CI` is present: NO
- environment secret storage target for `SEC-CI` is present: NO
- first real `SEC-CI` rehearsal may start now: NO

## 6) Next mainline after this preflight

Next task type:

- docs-only

Next task name:

- `G4 SEC-CI Storage Target Decision V1`

That next task should decide:

- whether `SEC-CI` will live at repo secret scope or another approved GitHub
  scope
- who owns creation / replacement
- what verification path will prove the target exists without exposing values

## 7) Explicit non-claims

- This preflight does not complete `Secret management and key rotation policy`.
- This preflight does not complete `G4`.
- This preflight does not create a GitHub secret target.
- This preflight does not rotate a secret.
- This preflight does not authorize go-live.
- This preflight does not authorize live trading.
- This preflight does not authorize real external requests.

## 8) Final preflight result

- no-plaintext scan path usable: YES
- current no-plaintext scan result: PASS
- SEC-CI storage target present now: NO
- first real SEC-CI rehearsal may start now: NO
- next task should remain docs-only: YES

# G4 Secret Inventory Completion And Rehearsal Packet V1

## 1) Current G4 state

- `G1 — Deployment and rollback drills pass`: DONE
- `G2 — P0/P1 alerting verified`: DONE
- `G3 — Backup/restore drill within RPO/RTO`: DONE
- `G4 — Security review complete (secrets + permissions + vuln baseline)`:
  NOT_DONE
- `Secret management and key rotation policy`: NOT_DONE
- go-live: NO-GO
- real external request: NOT AUTHORIZED
- live trading: NO-GO

## 2) Purpose of this packet

This packet does not rotate a real secret.

It does three narrower things:

1. completes the minimum inventory fields needed for the first rehearsal
2. selects the single first rehearsal candidate
3. defines the exact evidence packet for a future rehearsal run

## 3) First rehearsal candidate

Selected first rehearsal candidate:

- `SEC-CI`

Reason:

- already identified as the lowest-blast-radius recommendation in
  **`docs/SECRETS_AND_ROTATION.md`**
- touches CI verification rather than production runtime mutation
- can be rehearsed without changing deploy, trading, or external execution

## 4) Inventory completion target

For the first rehearsal candidate, the following inventory fields must be
explicitly complete before any real rotation starts:

| Secret ID | Description | Storage today | Owner role | Rotation interval |
|-----------|-------------|----------------|------------|---------------------|
| **SEC-CI** | CI tokens (GH PATs, deploy tokens) | GitHub repo / org secret store | Release manager | **90 days** |

The broader table in **`docs/SECRETS_AND_ROTATION.md`** may still contain
other placeholder rows after this packet, but the first rehearsal candidate
must have no ambiguity in:

- secret identifier
- storage location class
- owner role
- rotation interval

## 5) No-plaintext scan packet

Before any future rehearsal run, collect and preserve:

1. parent repo no-plaintext scan command
2. parent repo scan output
3. subtree / submodule scan references if they are part of the same release line
4. operator verdict:
   - `NO_PLAINTEXT_SCAN_RESULT=PASS|FAIL`

Minimum expected command family:

```bash
git grep -nE 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|secret[_-]?key\\s*=' -- ':!docs/' ':!RELEASE_NOTES.md' || true
```

This packet defines the evidence slot only. It does not run the scan.

## 6) Future rehearsal packet for SEC-CI

The future real rehearsal must capture all of the following:

- rehearsal candidate: `SEC-CI`
- pre-rotation timestamp
- operator identity
- old secret revoked only after replacement path is verified
- replacement secret installed in GitHub repo / org secret store
- post-rotation verification trigger recorded
- CI verification result recorded
- rollback path if CI verification fails

Required evidence placeholders:

- `SEC_CI_PRE_ROTATION_TIMESTAMP=...`
- `SEC_CI_OPERATOR=...`
- `SEC_CI_STORAGE_TARGET_VERIFIED=YES|NO`
- `SEC_CI_REPLACEMENT_CREATED=YES|NO`
- `SEC_CI_OLD_SECRET_REVOKED=YES|NO`
- `SEC_CI_POST_ROTATION_VERIFICATION_LINK=...`
- `SEC_CI_POST_ROTATION_RESULT=PASS|FAIL`
- `SEC_CI_ROLLBACK_PATH_USED=YES|NO`
- `SEC_CI_FINAL_VERDICT=PASS|FAIL`

## 7) Mandatory stop conditions

The future rehearsal must stop immediately if:

- the `SEC-CI` storage target is unclear
- the replacement secret cannot coexist long enough for verification
- any command/output would expose the secret value
- the post-rotation verification path is unclear
- the rollback path is unclear
- the rehearsal would mutate production runtime directly
- the rehearsal would authorize go-live, live trading, or real external requests

## 8) What remains NOT_DONE after this packet

Even after this packet exists:

- `Secret management and key rotation policy` remains NOT_DONE
- `G4` remains NOT_DONE
- no real rotation has yet occurred
- no no-plaintext scan result has yet been recorded

## 9) Explicit non-claims

- This packet does not rotate a real secret.
- This packet does not complete `Secret management and key rotation policy`.
- This packet does not complete `G4`.
- This packet does not authorize go-live.
- This packet does not authorize real external requests.
- This packet does not authorize live trading.

## 10) Final packet result

- first rehearsal candidate selected: YES
- first rehearsal candidate: `SEC-CI`
- inventory complete enough for first candidate planning: YES
- no-plaintext scan packet defined: YES
- future rehearsal evidence packet defined: YES
- real rotation rehearsal performed: NO
- secret management row ready for DONE: NO

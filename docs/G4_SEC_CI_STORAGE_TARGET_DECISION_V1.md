# G4 SEC-CI Storage Target Decision V1

## 1) Current G4 preflight result

- `NO_PLAINTEXT_SCAN_RESULT`: PASS
- `SEC-CI` storage target present: NO
- first real `SEC-CI` rehearsal may start: NO

Current fixed boundaries remain:

- production overwrite: NO
- real external request: NOT AUTHORIZED
- live trading: NO-GO
- go-live: NO-GO

## 2) Storage target placement decision

### Chosen storage target class

The first `SEC-CI` rehearsal target must be:

- GitHub repository Actions secret scope for `baolood/project-anchor`

This decision rejects, for the current first rehearsal:

- organization secret scope
- environment-only secret scope
- git-tracked files
- host-local runtime env files

### Responsible owner

Responsible owner for creation / replacement:

- Release manager

Working operator for the first bounded rehearsal may be the same human in the
current single-operator phase, but the role remains:

- Release manager

### Creation / replacement policy

The future first rehearsal must follow this policy:

1. create or replace only the selected `SEC-CI` target
2. do not touch unrelated GitHub secrets
3. verify presence without exposing the value
4. perform post-rotation verification before old secret retirement is treated
   as final

## 3) Presence-only verification method

Presence-only verification for the chosen storage target may use:

```bash
gh secret list --app actions
gh api repos/baolood/project-anchor/actions/secrets
```

Acceptable auditable output shape:

- repository identity confirmed
- secret inventory command executed
- `SEC_CI_STORAGE_TARGET_PRESENT=YES|NO`
- secret value never printed

This decision does **not** authorize:

- `gh secret set`
- workflow execution
- CI mutation
- secret value retrieval

The future bounded rehearsal may only proceed after the verification result is:

- `SEC_CI_STORAGE_TARGET_PRESENT=YES`

## 4) Mandatory stop conditions

Stop immediately if:

- target location is ambiguous
- ownership / replacement responsibility is unclear
- verification output is not auditable
- any command would execute the real rehearsal
- any command would print or reveal the secret value

## 5) G4 status after this decision

- storage target decision prepared: YES
- `SEC-CI` storage target present: NO
- first real rehearsal may start: NO

Why `NO` still holds:

- the target is now chosen, but it is not yet present
- no rehearsal execution may begin until the chosen target exists and is
  presence-verified

## 6) Explicit non-claims

- This decision does not execute rehearsal.
- This decision does not authorize production overwrite.
- This decision does not authorize live trading.
- This decision does not trigger external requests.
- This decision does not create or replace the secret target.

# G4 SEC-CI Storage Target Provisioning Operator Step V1

## 1) Current state

- `SEC-CI` storage target decision prepared: YES
- chosen storage target class: GitHub repository Actions secret scope
- `SEC-CI` storage target present now: NO
- first real `SEC-CI` rehearsal may start now: NO
- go-live: NO-GO
- real external request: NOT AUTHORIZED
- live trading: NO-GO

## 2) Purpose of this operator step

This step does not perform the `SEC-CI` rehearsal.

It only defines the minimum operator action needed to make the chosen storage
target exist so that a future rehearsal can pass precheck.

## 3) Responsible operator

Responsible role:

- Release manager

Current single-operator phase:

- the release manager and working operator may be the same person

## 4) Provisioning target

Provision the first `SEC-CI` target at:

- GitHub repository Actions secret scope for `baolood/project-anchor`

This step does not authorize:

- organization secret creation
- environment secret creation
- git-tracked secret storage
- host-local runtime secret storage

## 5) Provisioning action boundary

The future operator action may:

1. create one repository Actions secret for the selected `SEC-CI` rehearsal
   path
2. verify that the repository Actions secret inventory now shows the target as
   present

The future operator action may not:

- print the secret value
- store the secret in git-tracked files
- trigger a workflow run
- rotate any unrelated secret
- execute the real rehearsal in the same step

## 6) Presence-only verification

Presence-only verification may use:

```bash
gh secret list --app actions
gh api repos/baolood/project-anchor/actions/secrets
```

Required auditable output shape:

- repository identity confirmed
- operator timestamp recorded
- `SEC_CI_STORAGE_TARGET_PRESENT=YES|NO`
- secret value printed: NO

## 7) Mandatory stop conditions

Stop immediately if:

- the operator cannot verify they are acting on `baolood/project-anchor`
- the created target would land outside repository Actions secret scope
- verification output would expose the secret value
- any action would trigger the real rehearsal
- any action would mutate production runtime, deploy, or trading behavior

## 8) What remains not complete after this step

Even after the target is created:

- no-plaintext scan result still must be recorded as part of the rehearsal
- the actual `SEC-CI` rehearsal still remains unexecuted
- `Secret management and key rotation policy` remains NOT_DONE
- `G4` remains NOT_DONE

## 9) Explicit non-claims

- This operator step does not execute the real rehearsal.
- This operator step does not complete `Secret management and key rotation policy`.
- This operator step does not complete `G4`.
- This operator step does not authorize go-live.
- This operator step does not authorize real external requests.
- This operator step does not authorize live trading.

## 10) Final operator-step result

- storage target provisioning step prepared: YES
- chosen target scope fixed: YES
- operator role fixed: YES
- presence-only verification path fixed: YES
- real rehearsal executed by this step: NO

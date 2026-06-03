# G4 SEC-CI Value Source Confirmation And Provisioning Readiness Review V1

## Current G4 state

- `SEC-CI` value source decision prepared: `YES`
- `SEC-CI` value source confirmed: `NO`
- `SEC-CI` storage target present: `NO`
- provisioning result: `BLOCKED`
- blocker: `SEC_CI_VALUE_SOURCE_UNKNOWN`
- first real `SEC-CI` rehearsal may start: `NO`

Current fixed boundaries:

- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`
- `G1`: `DONE`
- `G2`: `DONE`
- `G3`: `DONE`
- `G4`: `NOT_DONE`

## Source confirmation checklist

The following must all be true before operator provisioning may proceed:

1. the authoritative `SEC-CI` value source is identified
2. the operator can retrieve the value privately without exposing it
3. the value is not copied into docs, chat, logs, or evidence records
4. the value is intended specifically for GitHub Actions secret `SEC_CI`
5. the value owner or source is recorded without revealing the value itself
6. the replacement and future rotation path is clear

## Provisioning readiness decision

Current readiness state:

- `SEC-CI` value source confirmed: `NO`
- operator provisioning may proceed: `NO`
- reason: `SEC_CI_VALUE_SOURCE_UNKNOWN`

This means the project may not yet enter the operator provisioning step.

## What would make it ready

Provisioning may proceed only after all of the following are true:

- the value source is actually confirmed
- the operator has private access to retrieve it
- the target repository identity is confirmed as `baolood/project-anchor`
- the storage target is confirmed as GitHub Actions secret `SEC_CI`
- the presence-only verification command set is prepared
- rehearsal remains forbidden until `SEC_CI_STORAGE_TARGET_PRESENT=YES`

## Manual operator action boundary

Once readiness becomes true, only the operator may run the following bounded provisioning flow:

- `gh repo view --json nameWithOwner`
- `printf '%s' '<real value>' | gh secret set SEC_CI --app actions`
- `gh secret list --app actions`
- `gh api repos/baolood/project-anchor/actions/secrets`

This review does **not** run those commands and does **not** claim they were run.

## Mandatory stop conditions

Stop immediately if any of the following are true:

- the value source is unknown
- value ownership is unclear
- the operator cannot retrieve the value privately
- the value would be printed
- command output would include the secret value
- rehearsal would start before presence-only verification
- repo identity is not `baolood/project-anchor`

## G4 status after this review

- `SEC-CI` value source confirmation review prepared: `YES`
- `SEC-CI` value source confirmed: `NO`
- operator provisioning may proceed: `NO`
- `SEC-CI` storage target present: `NO`
- first real `SEC-CI` rehearsal may start: `NO`
- `G4` ready for `DONE`: `NO`

## Explicit non-claims

- this review does not create `SEC_CI`
- this review does not confirm the value source
- this review does not execute rehearsal
- this review does not complete `G4`
- this review does not authorize go-live
- this review does not authorize live trading
- this review does not authorize real external requests

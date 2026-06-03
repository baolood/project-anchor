# G4 SEC-CI Rehearsal Execution Plan Preflight V1

## Current state

- `SEC_CI_STORAGE_TARGET_PRESENT`: `YES`
- secret value exposed: `NO`
- token type: `OPAQUE_BOUNDED_VALUE`
- operator has private access: `YES`
- rehearsal executed: `NO`
- `G4` ready for `DONE`: `NO`

Current boundaries remain unchanged:

- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`

## First bounded rehearsal objective

The future first bounded rehearsal should do only the following:

- run the no-plaintext scan
- verify `SEC_CI` presence without exposing the value
- perform a bounded GitHub Actions secret rotation or replacement rehearsal only if the already-approved docs and checklist path allow it
- capture non-secret evidence
- keep go-live, live trading, and real external request blocked

## Required precheck before any rehearsal

Before any real rehearsal runs, the future execution task must include all of the following:

1. repository identity check
2. git status check
3. current branch and main revision check
4. GitHub Actions secret inventory presence check
5. no-plaintext scan command
6. confirmation that the secret value is never printed
7. confirmation that the rehearsal command does not mutate production runtime
8. confirmation that no external request or live trading path is involved

## Mandatory stop conditions

Stop immediately if any of the following are true:

- `SEC_CI` is not present
- repo identity is not `baolood/project-anchor`
- no-plaintext scan finds real secret material
- command output would print the secret value
- rehearsal would modify unrelated secrets
- rehearsal would touch production runtime secrets
- workflow or rehearsal path is ambiguous
- go-live, live trading, or real external request would be enabled

## Planned evidence packet

The future rehearsal must capture the following non-secret evidence:

- repo identity
- git revision
- git status
- no-plaintext scan result
- `SEC_CI` presence-only result
- rehearsal action taken or explicitly not taken
- secret value exposed: `NO`
- old/new secret handling posture if rotation or replacement is performed
- rehearsal executed: `YES|NO`
- `G4` ready for `DONE`: `YES|NO`

## Status after this plan/precheck

- rehearsal execution plan/precheck prepared: `YES`
- `SEC_CI` storage target present: `YES`
- no-plaintext scan result reused/existing or required fresh before execution: `required fresh before execution`
- rehearsal executed: `NO`
- `G4` ready for `DONE`: `NO`

## Explicit non-claims

- this plan does not execute rehearsal
- this plan does not rotate or replace `SEC_CI`
- this plan does not complete `G4`
- this plan does not authorize go-live
- this plan does not authorize live trading
- this plan does not authorize real external requests

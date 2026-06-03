# G4 SEC-CI Value Source Confirmation Operator Handoff V1

## Current G4 blocked state

- `SEC-CI` value source confirmed: `NO`
- operator provisioning may proceed: `NO`
- `SEC-CI` storage target present: `NO`
- first real `SEC-CI` rehearsal may start: `NO`
- `G4` ready for `DONE`: `NO`
- blocker: `SEC_CI_VALUE_SOURCE_UNKNOWN`

Current boundaries remain unchanged:

- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`
- `G1`: `DONE`
- `G2`: `DONE`
- `G3`: `DONE`
- `G4`: `NOT_DONE`

## Operator handoff owner

- operator: `baolood`
- operator role: manually confirm the authoritative `SEC-CI` value source
- assistant/Codex role: cannot know, infer, generate, or receive the secret value
- disclosure rule: the secret value must never be pasted into chat, docs, logs, or any git-tracked file

## Confirmation checklist

The operator must confirm all of the following before provisioning:

1. the authoritative `SEC-CI` value source is identified
2. the source owner or source system is known
3. the operator can retrieve the value privately
4. the value is intended for GitHub Actions secret name `SEC_CI`
5. the target repository is `baolood/project-anchor`
6. the provisioning command is reviewed before execution
7. the presence-only verification command is prepared
8. rehearsal remains blocked until `SEC_CI_STORAGE_TARGET_PRESENT=YES`

## Confirmation result template

Operator-fillable result template:

- value source confirmed: `YES|NO`
- source type: `APPROVED_SYSTEM | APPROVED_OWNER | UNKNOWN`
- operator has private access: `YES|NO`
- secret value exposed: `NO`
- provisioning may proceed: `YES|NO`
- reason if `NO`: `<fill>`
- timestamp: `<fill>`

This template must never include the actual secret value.

## Provisioning readiness rule

Provisioning may proceed only if all of the following are true:

- value source confirmed: `YES`
- operator has private access: `YES`
- secret value exposed: `NO`
- target repo confirmed: `baolood/project-anchor`
- storage target name confirmed: `SEC_CI`
- rehearsal remains blocked

## Mandatory stop conditions

Stop immediately if any of the following are true:

- value source remains `UNKNOWN`
- source ownership is unclear
- operator cannot retrieve the value privately
- any instruction asks to paste the value into chat, docs, or logs
- target repo is not `baolood/project-anchor`
- a command would print the secret value
- rehearsal would run before presence-only verification

## G4 status after this handoff

- operator handoff prepared: `YES`
- `SEC-CI` value source confirmed: `NO`
- operator provisioning may proceed: `NO`
- `SEC-CI` storage target present: `NO`
- first real `SEC-CI` rehearsal may start: `NO`
- `G4` ready for `DONE`: `NO`

## Explicit non-claims

- this handoff does not confirm the value source
- this handoff does not create `SEC_CI`
- this handoff does not execute rehearsal
- this handoff does not complete `G4`
- this handoff does not authorize go-live
- this handoff does not authorize live trading
- this handoff does not authorize real external requests

# G4 SEC-CI Opaque Token Generation Decision V1

## Current discovery result

- `SEC-CI` expected type: `CI token / GH PAT / deploy token`
- documented owner: `Release manager`
- storage target: `GitHub repository Actions secret SEC_CI`
- existing GitHub Actions secret present: `NO`
- value generated or retrieved: `NO`
- operator private access: `NO`
- provisioning may proceed: `NO`

Current fixed boundaries:

- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`
- `G1`: `DONE`
- `G2`: `DONE`
- `G3`: `DONE`
- `G4`: `NOT_DONE`

## Source decision

For this first bounded rehearsal, the authoritative `SEC-CI` value source will be:

- a newly generated `Release manager`-controlled token

Allowed token/source class for this decision:

- newly generated CI token
- newly generated fine-grained GitHub PAT
- newly generated approved deploy token

Handling rules:

- the token must be created outside repo, docs, chat, and logs
- the token must be privately handled only by the operator
- the token value must never be written to docs or terminal output
- the token must be provisioned only into GitHub Actions secret name `SEC_CI`

## Minimum token posture

- use the minimum permission needed for the future rehearsal
- if the rehearsal only verifies presence, prefer a non-production, low-privilege, bounded token or opaque random value accepted by the rehearsal design
- if future workflow functionality requires GitHub access, use a fine-grained PAT with the narrowest repo/action permissions required
- do not use personal broad-scope tokens unless explicitly justified in a later review

## Readiness after this decision

- value source decision finalized: `YES`
- actual token generated: `NO`
- operator has private access: `NO`
- `SEC-CI` storage target present: `NO`
- operator provisioning may proceed: `NO`
- first real `SEC-CI` rehearsal may start: `NO`
- `G4` ready for `DONE`: `NO`

## Next allowed operator step

Only after this decision, the operator may privately create or retrieve the token and report a non-secret result:

- token generated or retrieved: `YES|NO`
- operator has private access: `YES|NO`
- secret value exposed: `NO`
- provisioning may proceed: `YES|NO`

No actual token creation is performed by this decision.

## Mandatory stop conditions

Stop immediately if:

- token value would be printed or copied into chat, docs, or logs
- operator cannot create or retrieve token privately
- token scope is broader than needed and not justified
- target repo is not `baolood/project-anchor`
- storage target name is not `SEC_CI`
- any command would execute rehearsal before presence-only provisioning

## Explicit non-claims

- this decision does not create the token
- this decision does not create `SEC_CI`
- this decision does not execute rehearsal
- this decision does not complete `G4`
- this decision does not authorize go-live
- this decision does not authorize live trading
- this decision does not authorize real external requests

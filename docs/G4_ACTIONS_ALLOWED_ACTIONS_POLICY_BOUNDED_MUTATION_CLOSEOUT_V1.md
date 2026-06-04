# G4 Actions Allowed Actions Policy Bounded Mutation Closeout V1

## 1. Repo and pre-mutation state

- repo identity: `baolood/project-anchor`
- git head before mutation: `27bff00`
- git status before mutation: `## main...origin/main`
- pre-mutation Actions enabled: `true`
- pre-mutation `allowed_actions`: `all`
- pre-mutation `sha_pinning_required`: `false`
- pre-mutation selected-actions endpoint result: `409 Conflict` because repository policy still allowed all actions and workflows

## 2. Bounded mutation performed

Performed mutation:

1. set repository Actions permissions from `allowed_actions: all`
2. to `allowed_actions: selected`
3. set selected-actions policy to:
   - `github_owned_allowed: true`
   - `verified_allowed: false`
   - `patterns_allowed: []`

Mutation scope:

- branch protection changed: `NO`
- secrets changed: `NO`
- runtime or production systems changed: `NO`
- unrelated GitHub settings changed: `NO`

## 3. Post-mutation state

- post-mutation Actions enabled: `true`
- post-mutation `allowed_actions`: `selected`
- post-mutation `sha_pinning_required`: `false`
- post-mutation `github_owned_allowed`: `true`
- post-mutation `verified_allowed`: `false`
- post-mutation `patterns_allowed`: `[]`

## 4. Workflow compatibility verification

Observed required workflow action references remain:

- `actions/checkout@v6`
- `actions/setup-python@v6`

Third-party actions observed: `NO`

Post-mutation CI verification:

- rerun target: `local-box-baseline` on `main`
- rerun completed: `YES`
- rerun result: `PASS`

## 5. Boundary

- permission changes performed: `YES`
- actions permissions changed: `YES`
- branch protection changed: `NO`
- secrets changed: `NO`
- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`
- `G4` ready for `DONE`: `NO`

## 6. What this closeout proves

- repository Actions policy was reduced from `all` to a bounded selected policy
- current required workflows still passed under the new policy
- the mutation stayed within the authorized scope

## 7. Explicit non-claims

- this closeout does not change branch protection
- this closeout does not complete `Permission minimization and audit`
- this closeout does not complete `G4`
- this closeout does not authorize go-live
- this closeout does not authorize live trading
- this closeout does not authorize real external requests

# G4 Actions Allowed Actions Policy Authorization Review V1

## 1. Current G4 state

- `G4` remaining blocker: `Permission minimization and audit`
- compatibility evidence collected: `YES`
- branch review mutation authorized: `NO`
- Actions policy mutation authorized before this review: `YES`
- permission changes performed so far: `NO`
- `G4` ready for `DONE`: `NO`

## 2. Current repository findings

- repo identity: `baolood/project-anchor`
- current Actions enabled: `true`
- current `allowed_actions`: `all`
- current `sha_pinning_required`: `false`

Observed required workflow action references:

- `actions/checkout@v6`
- `actions/setup-python@v6`

Third-party actions observed in `.github/workflows`: `NO`

## 3. Mutation under authorization review

Selected mutation:

- change repository Actions permissions from `allowed_actions: all`
- to a bounded policy compatible with the current workflow surface

Recommended bounded target for the first mutation:

- `allowed_actions: selected`
- selected actions limited to the currently required GitHub-owned actions and local repository actions only

This review does not apply the change. It only determines whether a future bounded mutation task may proceed.

## 4. Authorization decision

Current authorization result:

- Actions allowed actions policy mutation may proceed in a future bounded task: `YES`
- branch review requirement mutation may proceed in the same task: `NO`

Reason this action is authorized now:

- current workflow evidence shows only GitHub-owned actions
- no third-party action dependency was found in `.github/workflows`
- the official repository Actions permissions API supports moving from `all` to `selected`
- a rollback path is known

## 5. Required future bounded mutation shape

The future bounded mutation task must:

1. reconfirm repo identity
2. reconfirm current Actions permissions
3. set repository Actions permissions to the chosen bounded mode
4. if `selected` is used, set the selected-actions allowlist explicitly
5. rerun required CI
6. record rollback readiness

## 6. Mandatory stop conditions

Stop immediately if any of the following are true:

- repo identity is not `baolood/project-anchor`
- workflow references expand beyond the currently observed GitHub-owned or local actions
- the selected-actions allowlist cannot be expressed clearly
- rollback commands are unclear
- the mutation would also modify branch protection in the same step
- the mutation would touch secrets, runtime code, or production systems
- go-live, live trading, or real external request would be enabled

## 7. Rollback posture

If a future bounded mutation fails compatibility or breaks required checks, the rollback target is:

- restore repository Actions permissions to `allowed_actions: all`

This review does not execute the rollback.

## 8. Status after this review

- Actions policy authorization review prepared: `YES`
- Actions policy mutation authorized: `YES`
- branch review mutation authorized: `NO`
- permission changes performed: `NO`
- actions permissions changed: `NO`
- `G4` ready for `DONE`: `NO`

## 9. Explicit non-claims

- this review does not change Actions permissions
- this review does not change branch protection
- this review does not change secrets
- this review does not complete `G4`
- this review does not authorize go-live
- this review does not authorize live trading
- this review does not authorize real external requests

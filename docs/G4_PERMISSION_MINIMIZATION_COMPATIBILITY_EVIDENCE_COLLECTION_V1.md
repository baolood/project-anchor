# G4 Permission Minimization Compatibility Evidence Collection V1

## 1. Current state

- G4 selected remaining blocker: `Permission minimization and audit`
- compatibility precheck prepared: `YES`
- compatibility evidence collected before this document: `NO`
- permission changes performed so far: `NO`
- `G4` ready for `DONE`: `NO`

## 2. Read-only evidence collected

### Repository identity

- repo identity: `baolood/project-anchor`
- git head: `8a4a0e3`
- git status: `## main...origin/main`

### Current branch protection

- required status checks: `check`, `checklist-curl-guardrails`
- strict status checks: `true`
- enforce_admins: `true`
- required_approving_review_count: `0`
- required_signatures: `false`
- required_linear_history: `false`
- required_conversation_resolution: `false`

### Current Actions permissions

- Actions enabled: `true`
- allowed_actions: `all`
- sha_pinning_required: `false`

### Workflow action references

Observed `.github/workflows/local-box-baseline.yml` references:

- `actions/checkout@v6`
- `actions/setup-python@v6`

Third-party actions observed: `NO`

## 3. Compatibility assessment

### Action 1: Branch review requirement

- selected target: require at least `1` approving review
- compatibility result now: `NO`
- reason:
  - current collaborator evidence shows only the solo operator account in active admin use
  - no second reviewer availability is evidenced
  - enabling a non-zero required review count would likely create a merge block for the current workflow
- rollback command known: `YES`
- mutation authorized now: `NO`

Future rollback shape if this is ever tested in a bounded task:

- use the official pull request review protection endpoint to return `required_approving_review_count` to `0`

### Action 2: GitHub Actions allowed actions policy

- selected target: reduce from `all` to a bounded policy
- compatibility result now: `YES`
- reason:
  - current required workflow usage shows only GitHub-owned actions
  - no third-party action dependency was found in `.github/workflows`
  - official GitHub repository Actions permissions APIs support moving from `all` to `selected`
- rollback command known: `YES`
- mutation authorized now: `YES`, but only in a future bounded mutation task

Future rollback shape if this is ever changed:

- use the repository Actions permissions endpoint to restore `allowed_actions` to `all`

## 4. Official API basis

GitHub Docs confirms:

- repository Actions permissions support `allowed_actions` values `all`, `local_only`, and `selected`
- selected-actions configuration is only valid after repository permissions are set to `selected`
- pull request review protection supports setting `required_approving_review_count` between `0` and `6`

## 5. Decision after evidence collection

- compatibility evidence collected: `YES`
- branch review mutation authorized: `NO`
- Actions policy mutation authorized: `YES`
- permission mutation may proceed now: `PARTIAL`
- only safe next mutation path identified: `GitHub Actions allowed actions policy`
- remaining incompatible action: `Branch review requirement`

## 6. Boundary

- permission changes performed: `NO`
- branch protection changed: `NO`
- actions permissions changed: `NO`
- secrets changed: `NO`
- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`

## 7. Next step

Next single mainline:

- `G4 Actions Allowed Actions Policy Authorization Review V1`

This path is selected because:

- branch review requirement is not currently safe for the solo-operator workflow
- Actions policy restriction appears compatible with the current workflow surface

## 8. Explicit non-claims

- this evidence collection does not change branch protection
- this evidence collection does not change Actions permissions
- this evidence collection does not change secrets
- this evidence collection does not complete `G4`
- this evidence collection does not authorize go-live
- this evidence collection does not authorize live trading
- this evidence collection does not authorize real external requests

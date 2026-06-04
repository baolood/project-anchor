# G4 Permission Minimization Compatibility Precheck V1
## 1. Current state
- G4 selected remaining blocker: Permission minimization and audit
- Permission audit read-only inventory executed: YES
- Permission minimization actions selected: YES
- selected action count: 2
- permission changes performed so far: NO
- G4 — Security review complete: NOT_DONE
## 2. Selected actions under compatibility review
### Action 1: Branch review requirement
- current finding: required_approving_review_count: 0
- selected target: require at least 1 approving review if compatible with solo-operator workflow
- compatibility status before this precheck: UNKNOWN
- mutation authorized by this precheck: NO
### Action 2: GitHub Actions allowed actions policy
- current finding: allowed_actions: all
- selected target: reduce from all to a bounded allowlist or GitHub/local actions only if compatible with existing CI
- compatibility status before this precheck: UNKNOWN
- mutation authorized by this precheck: NO
## 3. Compatibility questions
Before any mutation, the project must answer:
### Branch review requirement
- Can required approving reviews be enabled without blocking the solo-operator PR workflow?
- Does GitHub allow the current admin/operator to merge when review count is greater than zero?
- Is there a second reviewer available if required?
- Would enabling this create an unrecoverable merge block?
- Is a rollback command known before mutation?
### Actions allowed actions policy
- Does local-box-baseline depend on third-party actions?
- Does the workflow use only GitHub-owned or local repository actions?
- Would restricting allowed actions break required checks?
- Is a rollback command known before mutation?
## 4. Required read-only evidence for next execution
The next read-only command collection must capture:
- repository identity
- current branch protection JSON
- current Actions permissions JSON
- workflow action references under .github/workflows
- whether workflows use third-party actions
- whether required review can be enabled safely
- whether Actions policy can be restricted safely
- rollback commands for each selected mutation
## 5. Provisional compatibility decision
- branch review requirement compatible now: UNKNOWN
- Actions allowed actions policy compatible now: UNKNOWN
- permission mutation may proceed now: NO
- reason: compatibility evidence not yet collected
- next step: run read-only compatibility evidence commands
## 6. Boundary
- permission_changes_performed: NO
- branch_protection_changed: NO
- actions_permissions_changed: NO
- secrets_changed: NO
- go-live: NO-GO
- real_external_request: NOT_AUTHORIZED
- live_trading: NO-GO
## 7. Status after this precheck
- compatibility precheck prepared: YES
- compatibility evidence collected: NO
- branch review mutation authorized: NO
- Actions policy mutation authorized: NO
- G4 ready for DONE: NO
## 8. Explicit non-claims
- This precheck does not change GitHub permissions.
- This precheck does not change branch protection.
- This precheck does not change Actions permissions.
- This precheck does not change secrets.
- This precheck does not complete G4.
- This precheck does not authorize go-live.
- This precheck does not authorize live trading.
- This precheck does not authorize real external requests.

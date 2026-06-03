# G4 Permission Minimization Action Selection V1

## 1. Current G4 state

- G4 selected remaining blocker: Permission minimization and audit
- Permission audit read-only inventory executed: YES
- Permission findings recorded: YES
- Permission changes performed so far: NO
- G4 — Security review complete: NOT_DONE

## 2. Read-only findings from inventory

Recorded findings:

- Actions allowed_actions: all
- Actions sha_pinning_required: false
- branch required_approving_review_count: 0
- branch required_signatures: false
- branch required_linear_history: false
- branch required_conversation_resolution: false

Existing protections already present:

- required_status_checks: enabled
- strict status checks: true
- required contexts:
  - check
  - checklist-curl-guardrails
- enforce_admins: true
- allow_force_pushes: false
- allow_deletions: false
- SEC_CI secret present: YES

## 3. Selected minimization actions

### 3.1 NOW_SELECTED

These are selected for the next bounded minimization planning/execution path:

1. Branch review requirement
   - current: required_approving_review_count: 0
   - selected target: require at least 1 approving review if compatible with solo-operator workflow
   - reason: merge protection is weak if required approving review count remains 0

2. GitHub Actions allowed actions policy
   - current: allowed_actions: all
   - selected target: reduce from all to a bounded allowlist or GitHub/local actions only if compatible with existing CI
   - reason: unrestricted actions are broader than needed for go-live posture

### 3.2 DEFERRED

These findings are real but not selected for immediate change in the next action:

1. required_signatures: false
   - deferred reason: may create signing friction and should not be changed without a separate signing-readiness review

2. required_linear_history: false
   - deferred reason: merge commits are currently used and changing this may disrupt the existing PR workflow

3. required_conversation_resolution: false
   - deferred reason: useful but lower priority than review requirement and Actions policy

4. sha_pinning_required: false
   - deferred reason: should be reviewed together with Actions allowlist compatibility, not changed blindly

## 4. Not selected for immediate direct mutation

This selection does not authorize direct setting changes.

The next task must still verify compatibility before any permission mutation, especially:

- whether solo-operator required review is feasible
- whether GitHub allows required reviews for the current repository/plan
- whether restricting Actions would break local-box-baseline
- whether current workflows rely on third-party actions
- whether a rollback command is known before mutation

## 5. Required next step

Next mainline:

- G4 Permission Minimization Compatibility Precheck

The next step must be read-only or planning-first unless all mutation commands and rollback commands are explicit.

## 6. Boundary

- permission_changes_performed: NO
- branch_protection_changed: NO
- actions_permissions_changed: NO
- secrets_changed: NO
- go-live: NO-GO
- real external request: NOT_AUTHORIZED
- live trading: NO-GO

## 7. Status after this selection

- minimization actions selected: YES
- selected action count: 2
- actual permission changes performed: NO
- G4 ready for DONE: NO

## 8. Explicit non-claims

- This selection does not change GitHub permissions.
- This selection does not change branch protection.
- This selection does not change Actions permissions.
- This selection does not change secrets.
- This selection does not complete G4.
- This selection does not authorize go-live.
- This selection does not authorize live trading.
- This selection does not authorize real external requests.

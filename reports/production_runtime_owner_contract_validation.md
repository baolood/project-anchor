# Production Runtime Owner Contract Validation

Generated at: `2026-07-30T09:19:16Z`

## Result

- result: BLOCKED

## Contract

- runtime identity: project-anchor-runtime
- runtime group: project-anchor-runtime
- canonical env path: `/etc/project-anchor/production.env`
- expected env owner: project-anchor-runtime
- expected env group: project-anchor-runtime
- expected env mode: 600
- interactive sudo required: NO
- group-based secret access: NO

## Observed Env Metadata

- exists: None
- owner: None
- group: None
- mode: None
- stat error: PERMISSION_DENIED

## Checks

- runtime_identity_explicit: PASS
- runtime_identity_resolved: FAIL
- runtime_group_explicit: PASS
- runtime_group_resolved: FAIL
- env_owner_expectation_explicit: PASS
- env_group_expectation_explicit: PASS
- env_mode_expectation_600: PASS
- env_file_exists: FAIL
- owner_match: FAIL
- group_match: FAIL
- mode_match: FAIL
- interactive_sudo_required_no: PASS
- group_based_secret_access_no: PASS
- owner_mismatch_fail_closed: PASS
- mode_mismatch_fail_closed: PASS
- identity_unresolved_fail_closed: PASS
- stat_permission_failure_fail_closed: PASS
- production_env_change_authorized_no: PASS
- owner_or_mode_change_authorized_no: PASS
- production_request_authorized_no: PASS
- go_live_no_go: PASS
- live_trading_no_go: PASS

## Errors

- runtime_identity_resolved
- runtime_group_resolved
- env_file_exists
- owner_match
- group_match
- mode_match

## Boundary

- production env changed: NO
- owner/mode changed: NO
- secret value read: NO
- secret value disclosed: NO
- production signing executed: NO
- production HTTP/network attempted: NO
- production request sent: NO
- production order sent: NO
- transport called when blocked: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

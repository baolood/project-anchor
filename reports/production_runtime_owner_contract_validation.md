# Production Runtime Owner Contract Validation

Generated at: `2026-07-30T10:06:19Z`

## Result

- result: PASS
- validation mode: macos_root_assisted_metadata_only

## Contract

- runtime identity: project_anchor_runtime
- runtime group: project_anchor_runtime
- canonical env dir: `/etc/project-anchor`
- canonical env path: `/etc/project-anchor/production.env`
- expected env dir owner: root
- expected env dir group: project_anchor_runtime
- expected env dir mode: 710
- expected env owner: project_anchor_runtime
- expected env group: project_anchor_runtime
- expected env mode: 600
- interactive sudo required: NO
- group-based secret access: NO

## Observed Env Directory Metadata

- exists: True
- owner: root
- group: project_anchor_runtime
- mode: 710
- stat error: None

## Observed Env Metadata

- exists: True
- owner: project_anchor_runtime
- group: project_anchor_runtime
- mode: 600
- stat error: None

## Checks

- running_as_root_for_metadata_only: PASS
- runtime_identity_explicit: PASS
- runtime_identity_resolved: PASS
- runtime_group_explicit: PASS
- runtime_group_resolved: PASS
- env_dir_exists: PASS
- env_dir_owner_match: PASS
- env_dir_group_match: PASS
- env_dir_mode_match: PASS
- env_file_exists: PASS
- owner_match: PASS
- group_match: PASS
- mode_match: PASS
- runtime_identity_can_read_env_file: PASS
- interactive_sudo_required_no: PASS
- group_based_secret_access_no: PASS
- production_env_change_authorized_no: PASS
- owner_or_mode_change_authorized_no: PASS
- production_request_authorized_no: PASS
- go_live_no_go: PASS
- live_trading_no_go: PASS

## Errors

- none

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

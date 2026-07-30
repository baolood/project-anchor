# Production Runtime Identity Provisioning Plan Validation

Generated at: `2026-07-30T09:58:46Z`

## Result

- result: PASS
- current runtime owner contract validation: BLOCKED

## Plan Target

- target runtime identity: project_anchor_runtime
- target runtime group: project_anchor_runtime
- target env dir: `/etc/project-anchor`
- target env dir owner: root
- target env dir group: project_anchor_runtime
- target env dir mode: 710
- target env path: `/etc/project-anchor/production.env`
- target env owner: project_anchor_runtime
- target env group: project_anchor_runtime
- target env mode: 600
- execution authorized: NO
- dry validation only: YES

## Checks

- runtime_identity_target_explicit: PASS
- runtime_group_target_explicit: PASS
- env_dir_target_explicit: PASS
- env_path_target_explicit: PASS
- target_identity_matches_contract: PASS
- target_group_matches_contract: PASS
- target_env_dir_matches_contract: PASS
- target_env_dir_owner_matches_contract: PASS
- target_env_dir_group_matches_contract: PASS
- target_env_dir_mode_710: PASS
- target_env_path_matches_contract: PASS
- target_env_owner_matches_contract: PASS
- target_env_group_matches_contract: PASS
- target_env_mode_600: PASS
- execution_authorized_no: PASS
- dry_validation_only_yes: PASS
- interactive_sudo_send_no: PASS
- secret_value_read_no: PASS
- production_request_authorized_no: PASS
- go_live_no_go: PASS
- live_trading_no_go: PASS
- create_group_step_present: PASS
- create_identity_step_present: PASS
- chown_step_targets_contract: PASS
- chmod_step_targets_600: PASS
- dir_chgrp_step_targets_contract: PASS
- dir_chmod_step_targets_710: PASS
- read_only_validation_step_present: PASS
- rollback_steps_present: PASS
- command_templates_no_send_or_network: PASS
- current_contract_validation_blocked: PASS

## Errors

- none

## Boundary

- provisioning executed: NO
- runtime identity created: NO
- runtime group created: NO
- production env changed: NO
- owner/mode changed: NO
- secret value read: NO
- secret value disclosed: NO
- sudo send executed: NO
- production signing executed: NO
- production HTTP/network attempted: NO
- production request sent: NO
- production order sent: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

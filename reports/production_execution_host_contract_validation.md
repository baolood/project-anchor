# Production Execution Host Contract Validation

Generated at: `2026-07-30T12:22:00Z`

## Result

- result: BLOCKED

## Expected

- hostname: vultr
- os_family: Linux
- repo_path: /root/project-anchor
- branch: main
- binance_api_ip_whitelist: 45.76.190.109
- runtime_identity: project_anchor_runtime

## Observed

- hostname: MacBook-Air
- os_family: Darwin
- repo_path: /Users/baolood/Projects/project-anchor
- branch: codex/project-anchor-production-execution-host-contract
- head: d220dc4
- git_status_short: M scripts/check_production_execution_readiness.py
?? config/production_execution_host_contract.json
?? scripts/validate_production_execution_host_contract.py
?? tests/test_production_execution_host_contract.py
- user: baolood

## Checks

- hostname_matches: False
- os_family_matches: False
- repo_path_matches: False
- branch_matches: False
- workspace_clean: False
- api_ip_whitelist_present: True
- runtime_identity_expected: True

## Errors

- hostname_matches
- os_family_matches
- repo_path_matches
- branch_matches
- workspace_clean

## Boundary

- credential_file_read: NO
- secret_value_read: NO
- secret_value_disclosed: NO
- dns_lookup: NO
- socket_opened: NO
- production_signing_executed: NO
- production_http_network_attempted: NO
- production_request_sent: NO
- production_order_sent: NO
- go_live: NO-GO
- live_trading: NO-GO

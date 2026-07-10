# Project Anchor Disabled-Only Runner Integration Implementation Authorization Prep V1

## Purpose

Prepare the authorization packet requirements for a future disabled-only runner integration implementation.

This is an authorization-prep artifact only. It does not fill an operator authorization packet, grant implementation authorization, modify runner/worker/risk, enable runtime execution, read credentials/env/config, add real signing, add real HTTP/network transport, send an external request, execute canary, authorize go-live, or authorize live trading.

## Baseline

- previous locked state: PROJECT_ANCHOR_DISABLED_ONLY_RUNNER_INTEGRATION_PLAN_MERGED_RUNTIME_DISABLED
- previous next safe state: READY_FOR_DISABLED_ONLY_RUNNER_INTEGRATION_IMPLEMENTATION_AUTHORIZATION_PREP
- current baseline HEAD: `834d7fa Merge pull request #279 from baolood/codex/project-anchor-disabled-only-runner-integration-plan`
- disabled-only runner integration plan present: YES
- runner / worker / risk remain unwired: YES
- runtime remains disabled: YES
- external request sent: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

## Future Authorization Packet Required Fields

A future implementation authorization packet must explicitly include:

- `AUTHORIZED_ACTION`
- `AUTHORIZED_SCOPE`
- `AUTHORIZED_ALLOWED_FILES`
- `AUTHORIZED_FORBIDDEN_FILES`
- `AUTHORIZED_RUNNER_CHANGES`
- `AUTHORIZED_WORKER_CHANGES`
- `AUTHORIZED_RISK_CHANGES`
- `AUTHORIZED_RUNTIME_PATH_ENABLEMENT`
- `AUTHORIZED_CREDENTIALS_ENV_CONFIG_READ`
- `AUTHORIZED_REAL_SIGNING`
- `AUTHORIZED_REAL_HTTP_NETWORK`
- `AUTHORIZED_EXTERNAL_REQUEST`
- `AUTHORIZED_CANARY`
- `AUTHORIZED_GO_LIVE`
- `AUTHORIZED_LIVE_TRADING`
- `REQUIRED_TESTS`
- `REQUIRED_ROLLBACK_PLAN`
- `FINAL_OPERATOR_VERDICT`

## Recommended Future Authorization Values

If the operator later chooses to authorize only the narrow disabled-only implementation, the future packet should remain bounded to:

- `AUTHORIZED_ACTION=implement_disabled_only_runner_integration_status_surface`
- `AUTHORIZED_SCOPE=disabled_status_surface_only`
- `AUTHORIZED_ALLOWED_FILES=anchor-backend/app/actions/runner.py;tests/test_alternative_testnet_http_client.py;docs/GO_LIVE_CHECKLIST.md`
- `AUTHORIZED_FORBIDDEN_FILES=anchor-backend/app/workers/*;anchor-backend/app/risk/*;anchor-backend/app/system/risk_gate.py;anchor-backend/app/system/risk_state.py;deploy;docker;migrations;env;credentials;DNS;TLS;ingress`
- `AUTHORIZED_RUNNER_CHANGES=YES_DISABLED_STATUS_ONLY`
- `AUTHORIZED_WORKER_CHANGES=NO`
- `AUTHORIZED_RISK_CHANGES=NO`
- `AUTHORIZED_RUNTIME_PATH_ENABLEMENT=NO`
- `AUTHORIZED_CREDENTIALS_ENV_CONFIG_READ=NO`
- `AUTHORIZED_REAL_SIGNING=NO`
- `AUTHORIZED_REAL_HTTP_NETWORK=NO`
- `AUTHORIZED_EXTERNAL_REQUEST=NO`
- `AUTHORIZED_CANARY=NO`
- `AUTHORIZED_GO_LIVE=NO`
- `AUTHORIZED_LIVE_TRADING=NO`
- `FINAL_OPERATOR_VERDICT=APPROVED_FOR_DISABLED_ONLY_IMPLEMENTATION`

This document does not set those values as approved. It only records the minimum future packet shape.

## Rejection Rules

The future packet must be rejected if:

- any required field is missing
- any required field is ambiguous
- the operator uses "continue", "agree", "go ahead", "next", or similar shorthand instead of explicit fields
- `AUTHORIZED_RUNTIME_PATH_ENABLEMENT` is not explicitly `NO`
- `AUTHORIZED_CREDENTIALS_ENV_CONFIG_READ` is not explicitly `NO`
- `AUTHORIZED_REAL_SIGNING` is not explicitly `NO`
- `AUTHORIZED_REAL_HTTP_NETWORK` is not explicitly `NO`
- `AUTHORIZED_EXTERNAL_REQUEST` is not explicitly `NO`
- `AUTHORIZED_CANARY` is not explicitly `NO`
- `AUTHORIZED_GO_LIVE` is not explicitly `NO`
- `AUTHORIZED_LIVE_TRADING` is not explicitly `NO`
- worker or risk changes are authorized without a separate dedicated review

## Future Implementation Guardrails

If a later packet is approved, implementation must still remain disabled-only:

- no worker invocation
- no risk policy change
- no command lifecycle advancement
- no signing call
- no transport call
- no credential/env/config read
- no external request
- no canary
- deterministic disabled result shape only

## Prep Result

DISABLED_ONLY_RUNNER_INTEGRATION_IMPLEMENTATION_AUTHORIZATION_PREP_RESULT=PASS

The next safe step is a separate operator authorization packet fill decision review. This prep does not authorize implementation or execution.

## Locked Boundary Preserved

- DNS changed: NO
- A/CNAME created: NO
- `45.76.190.109` bound: NO
- TLS requested: NO
- ingress opened: NO
- runner / worker / risk modified: NO
- runner / worker / risk wiring authorized: NO
- credentials/env/config read: NO
- real signing enabled: NO
- real HTTP/network enabled: NO
- runtime path enabled: NO
- external request sent: NO
- canary retried: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

## Final State

PROJECT_ANCHOR_DISABLED_ONLY_RUNNER_INTEGRATION_IMPLEMENTATION_AUTHORIZATION_PREP_MERGED_RUNTIME_DISABLED

## Next Safe State

NEXT_SAFE_STATE=READY_FOR_DISABLED_ONLY_RUNNER_INTEGRATION_IMPLEMENTATION_AUTHORIZATION_PACKET_FILL_DECISION_REVIEW

RUNTIME_REMAINS_DISABLED=YES

External request sent: NO

Canary executed: NO

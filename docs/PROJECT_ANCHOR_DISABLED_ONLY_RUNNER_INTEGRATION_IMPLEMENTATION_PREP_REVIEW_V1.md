# Project Anchor Disabled-Only Runner Integration Implementation Prep Review V1

## Purpose

Convert the operator-filled authorization packet into a concrete implementation-prep checklist for the future disabled-only runner integration status surface.

This is an implementation-prep review only. It does not modify runner code, worker code, risk code, enable runtime execution, read credentials/env/config, add real signing, add real HTTP/network transport, send an external request, execute canary, authorize go-live, or authorize live trading.

## Baseline

- previous locked state: PROJECT_ANCHOR_DISABLED_ONLY_RUNNER_INTEGRATION_AUTHORIZATION_PACKET_OPERATOR_FILL_MERGED_RUNTIME_DISABLED
- previous next safe state: READY_FOR_DISABLED_ONLY_RUNNER_INTEGRATION_IMPLEMENTATION_PREP_REVIEW
- current baseline HEAD: `e8fd78a Merge pull request #282 from baolood/codex/project-anchor-disabled-only-runner-integration-authorization-packet-operator-fill`
- operator authorization packet filled: YES
- implementation authorization granted for disabled-only runner status surface: YES
- implementation performed before this review: NO
- runtime remains disabled: YES
- external request sent: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

## Authorized Future Implementation Envelope

The future implementation is bounded to:

- action: `implement_disabled_only_runner_integration_status_surface`
- scope: `disabled_status_surface_only`
- runner changes: `YES_DISABLED_STATUS_ONLY`
- worker changes: `NO`
- risk changes: `NO`
- runtime path enablement: `NO`
- credentials/env/config reads: `NO`
- real signing: `NO`
- real HTTP/network: `NO`
- external request: `NO`
- canary: `NO`
- go-live/live trading: `NO`

## Allowed Files For Future Implementation

The future implementation may modify only:

- `anchor-backend/app/actions/runner.py`
- `tests/test_alternative_testnet_http_client.py`
- `docs/GO_LIVE_CHECKLIST.md`

The implementation should prefer the smallest possible subset. If the disabled status surface can be implemented without touching all allowed files, the unused allowed files must remain unchanged.

## Forbidden Files For Future Implementation

The future implementation must not modify:

- `anchor-backend/app/workers/*`
- `anchor-backend/app/risk/*`
- `anchor-backend/app/system/risk_gate.py`
- `anchor-backend/app/system/risk_state.py`
- deploy files
- docker files
- migrations
- env/config/credential files
- DNS/TLS/ingress/cloud-host binding files

## Required Future Implementation Shape

The future runner-facing surface must be deterministic and disabled-only. It should expose a local status shape equivalent to:

- `runtime_surface`: `alternative_testnet_http_client`
- `runtime_path_enabled`: false
- `runner_integration_mode`: `disabled_only`
- `stage`: `runner_disabled_surface`
- `reason`: `runtime_enablement_not_authorized`
- `network_sent`: false
- `external_order_id`: null
- `external_order_id_present`: false
- `credentials_read`: false
- `real_signing_enabled`: false
- `real_http_enabled`: false
- `worker_invoked`: false
- `risk_policy_changed`: false

The implementation must not expose secret values and must not depend on env/config.

## Required Future Tests

The implementation PR must add or update tests proving:

- runner-facing disabled result is deterministic
- `runtime_path_enabled` is false
- `network_sent` is false
- `external_order_id_present` is false
- `external_order_id` is null
- `credentials_read` is false
- `real_signing_enabled` is false
- `real_http_enabled` is false
- worker is not invoked
- risk policy is not changed
- signing and transport paths are not called
- no external request or canary is attempted

## Required Future Validation

The implementation PR must pass:

- HTTP client tests
- focused runner disabled surface test
- `git diff --check`
- `bash scripts/check_checklist_curl_guardrails.sh`
- `bash scripts/check_go_live_rules.sh`
- `bash scripts/check_local_box_baseline.sh`
- PR checks

## Rollback Plan

If the future implementation is merged and must be reverted:

1. revert the implementation PR
2. confirm runner disabled status surface is removed or restored to the previous state
3. confirm worker/risk files are unchanged
4. confirm runtime path remains disabled
5. confirm credentials/env/config are unread
6. confirm real signing and real HTTP remain disabled
7. confirm external request and canary remain absent

## Prep Review Result

DISABLED_ONLY_RUNNER_INTEGRATION_IMPLEMENTATION_PREP_REVIEW_RESULT=PASS

The next safe step is a separate disabled-only runner integration implementation slice. This review does not itself implement code.

## Locked Boundary Preserved

- DNS changed: NO
- A/CNAME created: NO
- `45.76.190.109` bound: NO
- TLS requested: NO
- ingress opened: NO
- runner / worker / risk modified in this task: NO
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

PROJECT_ANCHOR_DISABLED_ONLY_RUNNER_INTEGRATION_IMPLEMENTATION_PREP_REVIEW_MERGED_RUNTIME_DISABLED

## Next Safe State

NEXT_SAFE_STATE=READY_FOR_DISABLED_ONLY_RUNNER_INTEGRATION_IMPLEMENTATION_SLICE

RUNTIME_REMAINS_DISABLED=YES

External request sent: NO

Canary executed: NO

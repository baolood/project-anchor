# Project Anchor Disabled-Only Runner Integration Plan V1

## Purpose

Define a future disabled-only runner integration plan for surfacing HTTP client runtime status through runner-adjacent review surfaces without enabling runtime execution.

This is a planning artifact only. It does not authorize or implement runner wiring, worker wiring, risk wiring, runtime path enablement, credentials/env/config reads, real signing, real HTTP/network transport, external request, canary, go-live, or live trading.

## Baseline

- previous locked state: PROJECT_ANCHOR_DISABLED_ONLY_RUNNER_INTEGRATION_PLAN_PREP_MERGED_RUNTIME_DISABLED
- previous next safe state: READY_FOR_DISABLED_ONLY_RUNNER_INTEGRATION_PLAN
- current baseline HEAD: `09b53e2 Merge pull request #278 from baolood/codex/project-anchor-disabled-only-runner-integration-plan-prep`
- runner / worker / risk boundary reviewed: YES
- runner / worker / risk remain unwired: YES
- runtime remains disabled: YES
- external request sent: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

## Future Implementation Proposal Scope

Any future implementation proposal must be disabled-only and must surface status only. It must not create an execution path.

### Future Allowed Files

Only a separately authorized future implementation proposal may consider these files:

- `anchor-backend/app/actions/runner.py`
- `tests/test_alternative_testnet_http_client.py`
- `docs/GO_LIVE_CHECKLIST.md`

If future evidence shows a narrower implementation is possible, the narrower scope must be preferred.

### Future Forbidden Files

Unless separately authorized by a later operator-filled packet, the following remain forbidden:

- `anchor-backend/app/workers/command_worker.py`
- `anchor-backend/app/workers/domain_command_worker.py`
- `anchor-backend/app/risk/`
- `anchor-backend/app/system/risk_gate.py`
- `anchor-backend/app/system/risk_state.py`
- deploy, docker, migrations, env, credentials, DNS, TLS, ingress, and cloud-host binding files

## Proposed Runner-Facing Disabled Result Shape

A future disabled-only runner integration may only expose an audit-friendly disabled status shape equivalent to:

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

The shape must be deterministic and must not include secret values.

## Non-Execution Requirements

Any future implementation proposal must prove:

- disabled result generation does not call signing
- disabled result generation does not call transport
- disabled result generation does not read credentials/env/config
- disabled result generation does not create or mutate `external_order_id`
- disabled result generation does not set `network_sent=true`
- disabled result generation does not send external requests
- disabled result generation does not execute canary

## Worker And Risk Invariance Requirements

Any future implementation proposal must prove:

- worker files remain unchanged unless separately authorized
- risk files remain unchanged unless separately authorized
- command lifecycle authority remains commands_domain -> domain_command_worker
- runner status surfacing cannot advance command lifecycle state
- runner status surfacing cannot bypass risk policy
- runner status surfacing cannot invoke transport

## Required Tests For Future Implementation Proposal

The future implementation proposal must include tests that fail if:

- runner-facing disabled result omits `runtime_path_enabled=false`
- runner-facing disabled result omits `network_sent=false`
- runner-facing disabled result omits `external_order_id_present=false`
- runner-facing disabled result reports credentials as read
- runner-facing disabled result reports signing or HTTP as enabled
- worker or risk files are touched without authorization
- any implementation path attempts external request or canary

## Rollback Plan For Future Code Change

If a future implementation is authorized and merged, rollback must be limited to reverting the implementation PR. Rollback validation must confirm:

- runner-facing disabled status removed or restored to prior state
- worker/risk files unchanged or restored
- runtime path disabled
- credentials/env/config unread
- real signing disabled
- real HTTP/network disabled
- external request not sent
- canary not executed

## Authorization Requirement

This plan does not authorize implementation.

Before any code change, the operator must provide a separate explicit authorization packet that includes:

- exact authorized action
- exact allowed files
- exact forbidden files
- whether runner changes are authorized
- whether worker changes are authorized
- whether risk changes are authorized
- whether runtime path enablement is authorized
- whether credentials/env/config reads are authorized
- whether real signing is authorized
- whether real HTTP/network is authorized
- whether external request is authorized
- whether canary is authorized
- final operator verdict

Missing or ambiguous fields must be rejected.

## Plan Result

DISABLED_ONLY_RUNNER_INTEGRATION_PLAN_RESULT=PASS

The next safe step is a separate disabled-only runner integration implementation authorization prep. This plan does not authorize implementation or execution.

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

PROJECT_ANCHOR_DISABLED_ONLY_RUNNER_INTEGRATION_PLAN_MERGED_RUNTIME_DISABLED

## Next Safe State

NEXT_SAFE_STATE=READY_FOR_DISABLED_ONLY_RUNNER_INTEGRATION_IMPLEMENTATION_AUTHORIZATION_PREP

RUNTIME_REMAINS_DISABLED=YES

External request sent: NO

Canary executed: NO

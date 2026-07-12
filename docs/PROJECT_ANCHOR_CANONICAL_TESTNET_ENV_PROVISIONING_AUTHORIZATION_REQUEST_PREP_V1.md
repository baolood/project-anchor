# Project Anchor Canonical Testnet Env Provisioning Authorization Request Prep V1

## Locked Baseline

- Current locked state: `PROJECT_ANCHOR_CANONICAL_TESTNET_ENV_CONTRACT_AND_PROVISIONING_GAP_REVIEW_MERGED_RUNTIME_DISABLED`
- Latest main HEAD reviewed: `253a93c Merge pull request #295 from baolood/codex/project-anchor-canonical-testnet-env-contract-and-provisioning-gap-review`
- Canonical provisioning location: `/etc/project-anchor/testnet.env`
- Scope: documentation-only authorization request prep
- Provisioning performed in this task: NO
- Canonical env file created or modified in this task: NO
- Actual secret values read in this task: NO
- Secret values disclosed in this task: NO
- Second preflight executed in this task: NO
- Runtime enabled in this task: NO
- Signing in this task: NO
- HTTP/network in this task: NO
- External request in this task: NO
- Canary in this task: NO

## Purpose

This document only prepares a future operator authorization request for bounded provisioning of the canonical testnet env file identified by PR #295. It does not authorize provisioning by itself and does not create, read, or modify `/etc/project-anchor/testnet.env`.

## Explicit Non-Authorization

This document does not:

- provision credentials/env/config
- create or modify `/etc/project-anchor/testnet.env`
- read or disclose actual secret values
- execute a second preflight
- enable runtime
- execute signing
- enable HTTP/network
- authorize an external request
- authorize canary
- authorize go-live
- authorize live trading

## Locked Boundary Preserved

- credentials/env/config modified: NO
- actual secret values read: NO
- secret values disclosed: NO
- second preflight executed: NO
- runtime path enabled: NO
- real signing enabled: NO
- real HTTP/network enabled: NO
- external request sent: NO
- canary executed: NO
- go-live/live trading: NO-GO

## Required Fields From Reviewed Contract

The future provisioning request must cover exactly these canonical fields, without inventing values and without including example secret values:

- `TESTNET_EXCHANGE_BASE_URL`
- `TESTNET_EXCHANGE_API_KEY`
- `TESTNET_EXCHANGE_API_SECRET`
- `TESTNET_EXCHANGE_KEY_ID`
- `TESTNET_EXECUTOR_MODE`
- `TESTNET_EXECUTOR_REAL_ENABLE`

## Operator Fill Outcomes

Exactly one of the following outcomes may be selected by the operator. Missing fields, mixed outcomes, path drift, or ambiguous wording must be rejected.

### Option A: Approve Canonical Testnet Env Provisioning Only

```text
CANONICAL_TESTNET_ENV_PROVISIONING_AUTHORIZATION_REQUEST_FILLED=yes
AUTHORIZED_ACTION=provision_canonical_testnet_env_file_only
AUTHORIZED_SCOPE=create_or_update_etc_project_anchor_testnet_env_with_operator_supplied_values
AUTHORIZED_CANONICAL_PATH=/etc/project-anchor/testnet.env
AUTHORIZED_SECRET_VALUE_ENTRY=YES_BY_OPERATOR_ONLY
AUTHORIZED_SECRET_VALUE_DISCLOSURE=NO
AUTHORIZED_GIT_WRITE_OF_SECRETS=NO
AUTHORIZED_SHELL_OUTPUT_OF_SECRETS=NO
AUTHORIZED_LOGGING_OF_SECRETS=NO
AUTHORIZED_ENV_FILE_PERMISSION_HARDENING=YES
AUTHORIZED_PRESENCE_SHAPE_VALIDATION=YES
AUTHORIZED_RUNTIME_PATH_ENABLEMENT=NO
AUTHORIZED_REAL_SIGNING=NO
AUTHORIZED_REAL_HTTP_NETWORK=NO
AUTHORIZED_EXTERNAL_REQUEST=NO
AUTHORIZED_SECOND_PREFLIGHT=NO
AUTHORIZED_CANARY=NO
AUTHORIZED_GO_LIVE=NO
AUTHORIZED_LIVE_TRADING=NO
STOP_ON_ANY_SECRET_DISCLOSURE_RISK=YES
STOP_ON_ANY_PATH_MISMATCH=YES
STOP_ON_ANY_SCOPE_DRIFT=YES
FINAL_OPERATOR_VERDICT=APPROVED_FOR_CANONICAL_TESTNET_ENV_PROVISIONING_ONLY
SEPARATE_SECOND_PREFLIGHT_AUTHORIZATION_REQUIRED=YES
SEPARATE_RUNTIME_PATH_ENABLEMENT_AUTHORIZATION_REQUIRED=YES
SEPARATE_CANARY_AUTHORIZATION_REQUIRED=YES
SEPARATE_EXTERNAL_REQUEST_AUTHORIZATION_REQUIRED=YES
```

### Option B: Do Not Approve

```text
CANONICAL_TESTNET_ENV_PROVISIONING_AUTHORIZATION_REQUEST_FILLED=no
FINAL_OPERATOR_VERDICT=NOT_APPROVED
```

## Future Provisioning Requirements

A future separately authorized provisioning step must satisfy all of the following:

- operator supplies values directly
- values must never appear in Git
- values must never appear in PR, chat, closeout, terminal output, logs, or screenshots
- canonical path must be exactly `/etc/project-anchor/testnet.env`
- file ownership and permissions must be checked
- validation reports only `PRESENT_VALID`, `PRESENT_INVALID`, or `MISSING`
- no network-capable command may be used
- no service restart unless separately authorized
- no second preflight unless separately authorized
- no runtime path enablement unless separately authorized
- no external request unless separately authorized
- no canary unless separately authorized

## Interpretation Rules

- Option A authorizes bounded provisioning of `/etc/project-anchor/testnet.env` only.
- Option A does not authorize printing, copying, hashing, logging, or otherwise exposing secret values.
- Option A does not authorize writing secrets to Git or repository-managed files.
- Option A does not authorize service restart.
- Option A does not authorize a second preflight.
- Option A does not authorize runtime path enablement.
- Option A does not authorize signing.
- Option A does not authorize HTTP/network.
- Option A does not authorize external request.
- Option A does not authorize canary.
- Option A does not authorize go-live.
- Option A does not authorize live trading.
- Option B keeps the provisioning line paused.

NEXT_SAFE_STATE=WAITING_FOR_OPERATOR_FILL_ON_CANONICAL_TESTNET_ENV_PROVISIONING_AUTHORIZATION_REQUEST
RUNTIME_REMAINS_DISABLED=YES

## Recorded Operator Fill

The operator selected Option A for canonical testnet env provisioning only. This fill is documentation-only in this PR. It does not execute provisioning, does not create or modify `/etc/project-anchor/testnet.env`, does not read or disclose actual secret values, does not execute a second preflight, and does not enable runtime.

```text
CANONICAL_TESTNET_ENV_PROVISIONING_AUTHORIZATION_REQUEST_FILLED=yes
AUTHORIZED_ACTION=provision_canonical_testnet_env_file_only
AUTHORIZED_SCOPE=create_or_update_etc_project_anchor_testnet_env_with_operator_supplied_values
AUTHORIZED_CANONICAL_PATH=/etc/project-anchor/testnet.env
AUTHORIZED_SECRET_VALUE_ENTRY=YES_BY_OPERATOR_ONLY
AUTHORIZED_SECRET_VALUE_DISCLOSURE=NO
AUTHORIZED_GIT_WRITE_OF_SECRETS=NO
AUTHORIZED_SHELL_OUTPUT_OF_SECRETS=NO
AUTHORIZED_LOGGING_OF_SECRETS=NO
AUTHORIZED_ENV_FILE_PERMISSION_HARDENING=YES
AUTHORIZED_PRESENCE_SHAPE_VALIDATION=YES
AUTHORIZED_RUNTIME_PATH_ENABLEMENT=NO
AUTHORIZED_REAL_SIGNING=NO
AUTHORIZED_REAL_HTTP_NETWORK=NO
AUTHORIZED_EXTERNAL_REQUEST=NO
AUTHORIZED_SECOND_PREFLIGHT=NO
AUTHORIZED_CANARY=NO
AUTHORIZED_GO_LIVE=NO
AUTHORIZED_LIVE_TRADING=NO
STOP_ON_ANY_SECRET_DISCLOSURE_RISK=YES
STOP_ON_ANY_PATH_MISMATCH=YES
STOP_ON_ANY_SCOPE_DRIFT=YES
FINAL_OPERATOR_VERDICT=APPROVED_FOR_CANONICAL_TESTNET_ENV_PROVISIONING_ONLY
SEPARATE_SECOND_PREFLIGHT_AUTHORIZATION_REQUIRED=YES
SEPARATE_RUNTIME_PATH_ENABLEMENT_AUTHORIZATION_REQUIRED=YES
SEPARATE_CANARY_AUTHORIZATION_REQUIRED=YES
SEPARATE_EXTERNAL_REQUEST_AUTHORIZATION_REQUIRED=YES
```

## Post-Fill Boundary

- canonical env file modified by this fill PR: NO
- credentials/env/config provisioned by this fill PR: NO
- actual secret values read: NO
- secret values disclosed: NO
- second preflight executed: NO
- runtime path enabled: NO
- real signing enabled: NO
- real HTTP/network enabled: NO
- external request sent: NO
- canary executed: NO
- go-live/live trading: NO-GO

NEXT_SAFE_STATE_AFTER_OPERATOR_FILL=READY_FOR_BOUNDED_CANONICAL_TESTNET_ENV_PROVISIONING
RUNTIME_REMAINS_DISABLED=YES

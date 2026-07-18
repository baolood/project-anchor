# Project Anchor Second Bounded Preflight Authorization Request Prep V1

## Locked Baseline

- Current locked state: `PROJECT_ANCHOR_CANONICAL_TESTNET_ENV_PROVISIONING_PENDING_OPERATOR_LOCAL_SECRET_ENTRY_RUNTIME_DISABLED`
- Requested next state: `READY_FOR_SECOND_BOUNDED_PREFLIGHT_AUTHORIZATION_REQUEST_PREP`
- Latest merged baseline known before this prep: `a227450 Merge pull request #297 from baolood/codex/project-anchor-canonical-testnet-env-provisioning-authorization-request-operator-fill`
- Scope: documentation-only authorization request prep
- Second bounded preflight executed in this task: NO
- Credentials/env/config read in this task: NO
- Secret values read in this task: NO
- Runtime path enabled in this task: NO
- Real signing executed in this task: NO
- Real HTTP/network attempted in this task: NO
- External request sent in this task: NO
- Canary executed in this task: NO

## Purpose

This document prepares the operator authorization request required before a second bounded runtime enablement preflight may be executed after local canonical testnet env provisioning. It does not authorize or execute the preflight by itself.

The canonical env file remains operator-managed at:

```text
/etc/project-anchor/testnet.env
```

No secret values may be pasted into chat, committed to Git, printed to logs, captured in screenshots, or included in command arguments.

## Required Non-Secret Preconditions Before Operator Fill

A future operator fill for second bounded preflight execution must not be accepted until these non-secret facts are available:

- canonical env file path confirmed exactly: `/etc/project-anchor/testnet.env`
- file permission confirmed without content disclosure: mode `0600`
- parent directory protected from broad write access
- required field presence/shape validated without value disclosure
- repository guard defined for the execution moment
- runtime remains disabled before preflight
- no external request or canary has occurred as part of provisioning

## Required Field Status Inputs

The future operator fill or execution closeout may report only status markers for the following fields:

```text
TESTNET_EXCHANGE_BASE_URL=PRESENT_VALID / PRESENT_INVALID / MISSING
TESTNET_EXCHANGE_API_KEY=PRESENT_VALID / PRESENT_INVALID / MISSING
TESTNET_EXCHANGE_API_SECRET=PRESENT_VALID / PRESENT_INVALID / MISSING
TESTNET_EXCHANGE_KEY_ID=PRESENT_VALID / PRESENT_INVALID / MISSING
TESTNET_EXECUTOR_MODE=PRESENT_VALID / PRESENT_INVALID / MISSING
TESTNET_EXECUTOR_REAL_ENABLE=PRESENT_VALID / PRESENT_INVALID / MISSING
```

Actual values must never be disclosed.

## Explicit Non-Authorization

This prep document does not authorize:

- executing the second bounded preflight
- reading or printing secret values
- enabling the runtime path
- executing real signing
- enabling real HTTP/network
- sending an external request
- executing canary
- go-live
- live trading

## Future Operator Fill Outcomes

Exactly one outcome may be selected later by the operator. Missing fields, mixed outcomes, or ambiguous wording must be rejected.

### Option A: Approve Exactly One Second Bounded Preflight Only

```text
SECOND_BOUNDED_PREFLIGHT_AUTHORIZATION_REQUEST_FILLED=yes
AUTHORIZED_ACTION=execute_exactly_one_second_bounded_runtime_enablement_preflight_only
AUTHORIZED_SCOPE=presence_shape_validation_and_runtime_disabled_preflight_only
AUTHORIZED_CANONICAL_ENV_PATH=/etc/project-anchor/testnet.env
AUTHORIZED_CREDENTIALS_ENV_CONFIG_READ=YES_FOR_PREFLIGHT_ONLY
AUTHORIZED_SECRET_VALUE_DISCLOSURE=NO
AUTHORIZED_RUNTIME_PATH_ENABLEMENT=NO
AUTHORIZED_REAL_SIGNING=NO
AUTHORIZED_REAL_HTTP_NETWORK=NO
AUTHORIZED_EXTERNAL_REQUEST=NO
AUTHORIZED_CANARY=NO
AUTHORIZED_GO_LIVE=NO
AUTHORIZED_LIVE_TRADING=NO
STOP_ON_ANY_VALIDATION_FAILURE=YES
STOP_ON_ANY_SCOPE_DRIFT=YES
STOP_ON_ANY_NETWORK_ATTEMPT=YES
FINAL_OPERATOR_VERDICT=APPROVED_FOR_EXACTLY_ONE_SECOND_BOUNDED_PREFLIGHT_ONLY
SEPARATE_RUNTIME_PATH_ENABLEMENT_AUTHORIZATION_REQUIRED=YES
SEPARATE_EXTERNAL_REQUEST_AUTHORIZATION_REQUIRED=YES
SEPARATE_CANARY_AUTHORIZATION_REQUIRED=YES
```

### Option B: Do Not Approve

```text
SECOND_BOUNDED_PREFLIGHT_AUTHORIZATION_REQUEST_FILLED=no
FINAL_OPERATOR_VERDICT=NOT_APPROVED
```

## Future Preflight Output Requirements

A future separately authorized second bounded preflight must produce only non-secret evidence:

- workspace guard: PASS/FAIL
- baseline HEAD and clean-status evidence
- canonical env path exactness: PASS/FAIL
- file permission status: PASS/FAIL
- required field presence/shape status: PASS/FAIL
- runtime-disabled confirmation: PASS/FAIL
- secret values disclosed: NO
- signing executed: NO
- network attempted: NO
- external request sent: NO
- canary executed: NO
- final preflight verdict: PASS/FAIL

## Boundary Preserved In This Task

- second bounded preflight executed: NO
- credentials/env/config read: NO
- actual secret values read: NO
- secret values disclosed: NO
- runtime path enabled: NO
- real signing executed: NO
- real HTTP/network attempted: NO
- external request sent: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

NEXT_SAFE_STATE=WAITING_FOR_OPERATOR_FILL_ON_SECOND_BOUNDED_PREFLIGHT_AUTHORIZATION_REQUEST
RUNTIME_REMAINS_DISABLED=YES

## Recorded Operator Fill: Execution Prep Only

The operator selected a narrower documentation-only fill that allows preparation for a future second bounded preflight execution authorization step. This fill is not Option A preflight execution authorization, does not authorize reading `/etc/project-anchor/testnet.env`, and does not authorize preflight execution.

```text
SECOND_BOUNDED_PREFLIGHT_AUTHORIZATION_REQUEST_FILLED=yes
AUTHORIZED_ACTION=prepare_second_bounded_preflight_execution_only
AUTHORIZED_SCOPE=second_bounded_preflight_preparation_only
AUTHORIZED_PREFLIGHT_EXECUTION=NO
AUTHORIZED_CREDENTIALS_ENV_CONFIG_READ=NO
AUTHORIZED_SECRET_VALUE_READ_OR_DISCLOSURE=NO
AUTHORIZED_RUNTIME_PATH_ENABLEMENT=NO
AUTHORIZED_REAL_SIGNING=NO
AUTHORIZED_REAL_HTTP_NETWORK=NO
AUTHORIZED_EXTERNAL_REQUEST=NO
AUTHORIZED_CANARY=NO
AUTHORIZED_GO_LIVE=NO
AUTHORIZED_LIVE_TRADING=NO
FINAL_OPERATOR_VERDICT=APPROVED_FOR_SECOND_BOUNDED_PREFLIGHT_EXECUTION_PREP_ONLY
SEPARATE_PREFLIGHT_EXECUTION_AUTHORIZATION_REQUIRED=YES
```

## Post-Fill Boundary

- second bounded preflight executed by this fill: NO
- `/etc/project-anchor/testnet.env` read by this fill: NO
- credentials/env/config read by this fill: NO
- actual secret values read or disclosed: NO
- runtime path enabled: NO
- real signing executed: NO
- real HTTP/network attempted: NO
- external request sent: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

NEXT_SAFE_STATE_AFTER_OPERATOR_FILL=WAITING_FOR_REMOTE_PR_AUTHORIZATION_FOR_SECOND_BOUNDED_PREFLIGHT_OPERATOR_FILL
RUNTIME_REMAINS_DISABLED=YES

# Approved Alternative Testnet Implementation Plan V1

## 1. Purpose

Prepare a minimal implementation plan for one approved official alternative testnet, sandbox, demo, or paper-trading venue after the approved alternative testnet canary prep was merged.

This artifact is planning only:

- alternative venue executor implemented: NO
- backend / worker / risk / deploy changed: NO
- runtime behavior changed: NO
- credentials added or changed: NO
- external request sent in this task: NO
- canary retried in this task: NO
- DB mutation performed in this task: NO
- executor / network / location / proxy / VPN changed: NO

## 2. Current State

- approved alternative testnet canary prep merged: YES
- source prep: `docs/APPROVED_ALTERNATIVE_TESTNET_CANARY_PREP_V1.md`
- Binance canary result remains FAILED/http_451: YES
- Binance same-path retry rejected: YES
- ad hoc VPN/proxy workaround rejected: YES
- canary authorized: NO
- external request authorized: NO
- live trading: NO-GO
- go-live: NO-GO

## 3. Implementation Goal

Future work may prepare support for one approved official alternative testnet/sandbox venue while preserving the current Project Anchor evidence model:

- support one approved official alternative testnet/sandbox venue
- preserve exactly-one request evidence
- preserve DONE / FAILED event chain evidence
- preserve no-real-money exposure
- preserve existing runner semantics
- preserve explicit authorization before credentials, runtime changes, or execution

## 4. Required Future Implementation Boundary

Any future implementation must remain a separate, explicitly authorized PR:

- implementation must be a separate PR
- credential setup must be separately authorized
- canary execution must be separately authorized
- no live trading
- no go-live
- no retry without new authorization
- no automatic fallback from testnet/sandbox to live
- no secret values in docs, tests, logs, or PR descriptions

This plan does not authorize implementation, credentials, runtime changes, canary retry, external requests, go-live, or live trading.

## 5. Candidate Implementation Surface

The future implementation surface is planning-level only and must be narrowed again before code changes:

### Executor adapter boundary

- add one minimal alternative testnet executor adapter only after authorization
- keep the existing command runner semantics intact
- keep `commands_domain -> domain_command_worker -> DONE / FAILED` as the evidence surface
- avoid broad exchange abstraction unless a later review proves it is necessary

### Config and environment names only

Future implementation may define placeholder names only, not values:

- `ALTERNATIVE_TESTNET_VENUE`
- `ALTERNATIVE_TESTNET_BASE_URL`
- `ALTERNATIVE_TESTNET_API_KEY_PRESENT`
- `ALTERNATIVE_TESTNET_API_SECRET_PRESENT`
- `ALTERNATIVE_TESTNET_CREDENTIAL_PROFILE`

No secret value may be printed, committed, pasted into docs, or emitted in logs.

### Testnet base URL placeholder

- use a placeholder until the selected venue/access path is separately reviewed
- no production endpoint may be used
- no live trading endpoint may be used
- no same-path Binance retry is authorized by this plan

### Idempotency behavior

- preserve the Project Anchor idempotency key as the primary operator evidence
- map to a venue client-order-id field only if the selected venue supports it
- duplicate idempotency must not create a second external order request
- no automatic retry on incomplete evidence

### External order evidence rules

- record external_order_id presence/absence based on actual result
- never infer success from request submission alone
- terminal evidence must remain DONE / FAILED with event chain support

### Failure family mapping

Future implementation should map venue failures into explicit families, such as:

- `ALTERNATIVE_TESTNET_EXECUTOR_ACCEPTED`
- `ALTERNATIVE_TESTNET_EXECUTOR_REJECTED`
- `ALTERNATIVE_TESTNET_EXECUTOR_FAILED`
- `ALTERNATIVE_TESTNET_CREDENTIALS_MISSING`
- `ALTERNATIVE_TESTNET_ACCESS_BLOCKED`
- `ALTERNATIVE_TESTNET_UNEXPECTED`

Exact names may be refined in the authorized implementation PR, but the mapping must remain explicit and tested.

### Event chain expectations

A future accepted/rejected/failed attempt must preserve an auditable event chain comparable to:

- `PICKED`
- `POLICY_ALLOW`
- `KILL_SWITCH_CHECKED`
- `TESTNET_EXECUTOR_REQUESTED`
- venue-specific accepted / rejected / failed event
- `ACTION_DONE` or `ACTION_FAIL`
- `MARK_DONE` or `MARK_FAILED`

## 6. Forbidden Implementation Shortcuts

The following shortcuts are forbidden:

- no ad hoc VPN/proxy workaround
- no production endpoint
- no live credentials
- no reused Binance assumptions unless explicitly compatible and reviewed
- no automatic retry
- no fallback from testnet/sandbox to live
- no broad exchange abstraction by default
- no credential value printing
- no go-live or live trading escalation

## 7. Expected Future Validation

A future implementation PR must validate at minimum:

- adapter success path unit test
- adapter rejected path unit test
- adapter failed path unit test
- duplicate idempotency behavior test
- missing credentials / credential presence-only guard test
- no credential leakage in logs or docs
- no external request during implementation PR tests
- hardened one-shot guardrail PASS
- go-live rules PASS
- local box baseline PASS
- git diff --check PASS

## 8. Rollback Shape For Future Implementation

If a future implementation PR is wrong before execution, revert only that implementation PR.

If a future canary execution has already occurred, do not attempt to erase the request. Record the result, stop, and close out the evidence. Any retry requires new authorization.

## 9. Boundary Preserved

- canary retried: NO
- external request sent in this task: NO
- DB mutation performed in this task: NO
- simulator replay executed: NO
- executor / network / location / proxy / VPN changed: NO
- backend / worker / risk / deploy changed: NO
- runtime / env / secrets changed: NO
- credentials changed: NO
- live trading: NO-GO
- go-live: NO-GO

## 10. Next Safe Status

- `READY_FOR_APPROVED_ALTERNATIVE_TESTNET_IMPLEMENTATION_PLAN_PR_MERGE`

After this plan is merged and baseline is clean, the next possible status is an explicitly authorized implementation slice. This plan does not authorize code changes, credential setup, canary retry, external requests, go-live, or live trading.

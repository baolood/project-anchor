# First real request review artifact example - BLOCKED

**Status:** synthetic example only - no real key, no external API call, no live trading approval.

**Purpose:** show what a filled first-real-request signoff artifact should look like for a `BLOCKED` outcome, using synthetic values only.

**Canonical path only:**

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This file is an example artifact under the storage posture defined by:

- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_STORAGE_LOCATION_DECISION_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_STORAGE_LOCATION_DECISION_V1.md)
- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md)

It is not evidence of a real request having been sent.

## 1. Example filled record

```text
record_id: first-real-request-example-2026-05-23
review_date: 2026-05-23
reviewer: baolood
operator: baolood
witness: none

executor_mode: real
real_wire_guard_state: disabled
host_label: binance_futures_testnet
configured_origin: https://testnet.binancefuture.com
kill_switch_source_confirmed: yes
credential_presence_confirmed: no

command_type: ORDER
execution_mode: testnet
market: binance_testnet
symbol: BTCUSDT
side: BUY
notional: 4.0
order_type: market
stop_price: 68000.0
source: ops_manual
created_by: baolood
idempotency_key: example-first-real-request-2026-05-23

readiness_bundle_reviewed: yes
enablement_checklist_completed: no
retreat_posture_rehearsed: yes
live_trading_no_go_confirmed: yes

command_id: not-sent
final_result_label: BLOCKED
final_command_state: not sent
normalized_family: TESTNET_CREDENTIALS_MISSING
external_request_status: no
retreat_required: no

notes: The request remained blocked because canonical credential presence could not be confirmed safely and the enablement checklist was therefore incomplete. Runtime posture remained fail-closed before any external attempt. No second attempt is allowed until credentials, checklist completion, and reviewer signoff are all explicit.
```

## 2. Why this example is `BLOCKED`

This example is intentionally blocked because:

- `TESTNET_EXECUTOR_MODE=real` alone is not enough
- canonical credential presence was not confirmed
- the enablement checklist was not fully complete
- no `command_id` was created for a real external attempt
- no signed HTTP was allowed to begin

This is the correct posture when any pre-enable requirement is still ambiguous.

## 3. What evidence should still be absent

For a synthetic `BLOCKED` example like this, these must remain absent:

- `TESTNET_EXECUTOR_REQUESTED`
- `TESTNET_EXECUTOR_ACCEPTED`
- `TESTNET_EXECUTOR_REJECTED`
- `external_order_id`
- `external_status`
- any secret material

This preserves the distinction between:

```text
request blocked before external attempt
```

and:

```text
request attempted and later failed
```

## 4. How to use this example

Use this file as a style reference only:

- to see how the signoff record fields can be filled
- to verify that `BLOCKED` can still produce a useful review artifact
- to keep future real-request evidence non-secret and correlated

Do not cite this file as proof that the repo has already performed a real external testnet request.

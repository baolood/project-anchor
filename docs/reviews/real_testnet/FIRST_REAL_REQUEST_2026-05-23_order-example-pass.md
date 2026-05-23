# First real request review artifact example - PASS

**Status:** synthetic example only - no real key, no external API call, no live trading approval.

**Purpose:** show what a filled first-real-request signoff artifact should look like for a `PASS` outcome, using synthetic values only.

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
record_id: first-real-request-pass-example-2026-05-23
review_date: 2026-05-23
reviewer: baolood
operator: baolood
witness: none

executor_mode: real
real_wire_guard_state: enabled
host_label: binance_futures_testnet
configured_origin: https://testnet.binancefuture.com
kill_switch_source_confirmed: yes
credential_presence_confirmed: yes

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
idempotency_key: example-first-real-request-pass-2026-05-23

readiness_bundle_reviewed: yes
enablement_checklist_completed: yes
retreat_posture_rehearsed: yes
live_trading_no_go_confirmed: yes

command_id: order-example-pass-2026-05-23
final_result_label: PASS
final_command_state: DONE
normalized_family: canonical_real_testnet_success
external_request_status: accepted
retreat_required: no

notes: The synthetic first request example is treated as PASS because the canonical ORDER testnet path was used, runtime posture was explicit, `/commands/[id]` would be reviewable, and the example event chain is internally consistent with a bounded accepted upstream request. No anomaly is assumed, and no second request is implied by this example alone.
```

## 2. Why this example is `PASS`

This example is intentionally marked `PASS` because it assumes:

- canonical credential presence was confirmed safely
- enablement checklist was complete
- runtime posture was intentionally `real`
- review evidence remained consistent from command to result
- no contradiction appeared between host/origin identity and final acceptance evidence

This is the narrow definition of a PASS-worthy first request artifact.

## 3. What evidence should be present

For a synthetic `PASS` example like this, the expected evidence family would be:

- `TESTNET_EXECUTOR_REQUESTED`
- `TESTNET_EXECUTOR_ACCEPTED`
- `ACTION_OK`
- `MARK_DONE`
- `external_order_id`
- `external_status`

And the result should remain reviewable without secrets.

## 4. What evidence should still be absent

Even for a synthetic `PASS` example, these must remain absent:

- `TESTNET_EXECUTOR_STUB`
- preflight refusal disguised as acceptance
- secret material in result or event payload
- ambiguous host label or configured origin

This keeps the success record consistent with the canonical real-attempt contract.

## 5. How to use this example

Use this file as a style reference only:

- to see how a PASS-worthy review artifact can be filled
- to compare against the synthetic `BLOCKED` example
- to understand what “accepted external request” evidence should look like in record form

Do not cite this file as proof that the repo has already performed a real external testnet request.

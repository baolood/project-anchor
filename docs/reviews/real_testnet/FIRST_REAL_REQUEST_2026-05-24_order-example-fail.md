# First real request review artifact example - FAIL

**Status:** synthetic example only - no real key, no external API call, no live trading approval.

**Purpose:** show what a filled first-real-request signoff artifact should look like for a `FAIL` outcome, using synthetic values only.

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
record_id: first-real-request-fail-example-2026-05-24
review_date: 2026-05-24
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
idempotency_key: example-first-real-request-fail-2026-05-24

readiness_bundle_reviewed: yes
enablement_checklist_completed: yes
retreat_posture_rehearsed: yes
live_trading_no_go_confirmed: yes

command_id: order-example-fail-2026-05-24
final_result_label: FAIL
final_command_state: FAILED
normalized_family: TESTNET_EXECUTOR_UNEXPECTED
external_request_status: attempted
retreat_required: yes

notes: The synthetic first request example is treated as FAIL because the path crossed the external boundary, but the resulting evidence was contradictory: the request looked attempted, yet the downstream acceptance or rejection evidence could not be reconciled cleanly. Retreat to mock or fail-closed posture is required before any second attempt.
```

## 2. Why this example is `FAIL`

This example is intentionally marked `FAIL` because it assumes:

- runtime posture was explicit enough to send the request
- the request crossed into external-attempt territory
- the resulting evidence could not be explained safely
- the team must retreat before any second attempt

This is different from `BLOCKED`, where the request never should have started, and different from `PASS`, where the evidence remains internally consistent.

## 3. What evidence should be present

For a synthetic `FAIL` example like this, the expected evidence family would include:

- `TESTNET_EXECUTOR_REQUESTED`
- `TESTNET_EXECUTOR_REJECTED` or otherwise contradictory external-attempt evidence
- `ACTION_FAIL`
- `MARK_FAILED`

The key point is that the path already crossed the external boundary and still did not produce a safely reviewable outcome.

## 4. What makes this a fail-worthy contradiction

Examples of contradiction that justify `FAIL` rather than `BLOCKED`:

- external attempt is evident, but normalized family is not trustworthy
- `/commands/[id]` explanation disagrees with raw event chain
- host/origin identity looks mismatched after request start
- result suggests external attempt, but acceptance/rejection evidence is incomplete

If the first request cannot be explained safely after it was attempted, it must not be treated as `PASS`.

## 5. How to use this example

Use this file as a style reference only:

- to see how a FAIL-worthy review artifact can be filled
- to compare against the synthetic `BLOCKED` and `PASS` examples
- to understand when retreat should become mandatory

Do not cite this file as proof that the repo has already performed a real external testnet request.

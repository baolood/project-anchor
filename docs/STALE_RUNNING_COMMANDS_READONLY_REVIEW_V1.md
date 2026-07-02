# Stale Running Commands Readonly Review V1

## 1. Purpose

- review the stale `RUNNING` commands that blocked canary preflight
- prepare a cleanup recommendation
- no database mutation
- no canary retry
- no real external exchange request

This review is read-only. It does not mark commands DONE or FAILED, unlock commands, delete commands, restart workers, or change runtime behavior.

## 2. Canary Preflight Blocker

- canary preflight blocked: YES
- canary request sent: NO
- external request sent: NO
- final status: `PREFLIGHT_BLOCKED`
- blocker: 2 stale `RUNNING` commands in `commands_domain`
- next safe status before this review: `CANARY_PREFLIGHT_BLOCKED_BY_UNEXPECTED_RUNNING_COMMANDS`

## 3. Commands Reviewed

### order-e66c32df-4c14-4dd0-b23e-dce6a8835740

- command_id: `order-e66c32df-4c14-4dd0-b23e-dce6a8835740`
- type: ORDER
- status: RUNNING
- attempt: 1
- locked_by: `domain-worker`
- locked_at: `2026-06-07 09:30:42.199177+00`
- created_at: `2026-06-07 09:30:41.393054+00`
- updated_at: `2026-06-07 09:30:42.199177+00`
- result: NULL
- error: NULL
- payload idempotency_key: `testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1`
- payload execution_mode: `testnet`
- payload market: `binance_testnet`

Event chain:

```text
PICKED
-> POLICY_ALLOW
```

Evidence summary:

- last event: `POLICY_ALLOW`
- MARK_DONE present: NO
- MARK_FAILED present: NO
- external request event present: NO
- external_order_id / simulator_order_id field present: NO
- recommendation: `SAFE_TO_MARK_FAILED_WITH_STALE_RUNNING_REASON`

### order-fec6a82f-b8fe-4f4c-ae45-972aaf26e91e

- command_id: `order-fec6a82f-b8fe-4f4c-ae45-972aaf26e91e`
- type: ORDER
- status: RUNNING
- attempt: 1
- locked_by: `domain-worker`
- locked_at: `2026-06-08 01:13:41.77672+00`
- created_at: `2026-06-08 01:13:41.136807+00`
- updated_at: `2026-06-08 01:13:41.77672+00`
- result: NULL
- error: NULL
- payload idempotency_key: `testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1`
- payload execution_mode: `testnet`
- payload market: `binance_testnet`

Event chain:

```text
PICKED
-> POLICY_ALLOW
```

Evidence summary:

- last event: `POLICY_ALLOW`
- MARK_DONE present: NO
- MARK_FAILED present: NO
- external request event present: NO
- external_order_id / simulator_order_id field present: NO
- recommendation: `SAFE_TO_MARK_FAILED_WITH_STALE_RUNNING_REASON`

## 4. Read-Only DB Inspection

- commands inspected read-only: YES
- domain_events inspected read-only: YES
- UPDATE performed: NO
- DELETE performed: NO
- INSERT performed: NO
- commands marked DONE: NO
- commands marked FAILED: NO
- commands unlocked: NO
- worker restarted: NO

## 5. Cleanup Recommendation

Both stale `RUNNING` commands appear safe candidates for a separately authorized minimal cleanup plan:

- target action: mark each command `FAILED`
- reason label: `STALE_RUNNING_PRE_CANARY_CLEANUP`
- preserve original payload/result/error evidence
- append or record cleanup evidence if the project has an accepted event/audit path
- do not retry either command
- do not send canary in the cleanup task
- do not send any real external exchange request

The cleanup itself is not authorized by this review.

## 6. Final State

- stale RUNNING review added: YES
- cleanup executed: NO
- canary executed: NO
- live trading: NO-GO
- go-live: NO-GO
- next safe status: `READY_FOR_STALE_RUNNING_COMMANDS_CLEANUP_PLAN`

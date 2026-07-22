# Production Execution Handoff Snapshot

Generated at: `2026-07-22T01:50:00Z`

## Result

- result: PASS
- handoff status: READY_FOR_DECISION
- next gate: EXPLICIT_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_AUTHORIZATION

## Testnet Baseline

- controlled request: `order-a06eed8f-cd60-4a4f-b3e9-84c540b98e6f` / DONE / FILLED
- controlled external order id present: True
- controlled executed at: `2026-07-18T15:39:27.590704+00:00`
- canary: `order-f4fd182a-7a66-4f3c-a69f-f0a212c2c420` / DONE / FILLED
- canary external order id present: True
- canary executed at: `2026-07-19T05:55:03.323572+00:00`

## Production State

- entrypoint present: true
- command creation candidate: true
- non-executable command id: `prod-order-drill-20260722T013656Z`
- non-executable command status: `CREATED_NOT_EXECUTABLE`
- worker executable: false
- send authorized: false
- production request sent: false

## Checks

- controlled_request_filled: PASS
- canary_filled: PASS
- production_entrypoint_present: PASS
- production_command_candidate_available: PASS
- production_non_executable_command_created: PASS
- production_send_not_authorized: PASS
- production_request_not_sent: PASS
- go_live_no_go: PASS
- go_live_blockers_explicit: PASS
- send_window_plan_present: PASS
- send_window_not_authorized: PASS
- pre_send_chain_complete: PASS

## Go-Live Blocking Gates

- production credential access not authorized
- production signing not approved
- production HTTP/network execution not approved
- rollback and stop conditions not approved for go-live
- monitoring window not approved for go-live
- go-live authorization not granted
- live trading authorization not granted

## Errors

- none

## Boundary

- secret read: NO
- production signing executed: NO
- DNS lookup performed: NO
- socket opened: NO
- production HTTP/network executed: NO
- production request sent: NO
- canary rerun: NO
- go-live: NO-GO
- live trading: NO-GO

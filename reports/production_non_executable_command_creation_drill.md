# Production Non-Executable Command Creation Drill

Generated at: `2026-07-22T01:36:56Z`

## Result

- result: PASS
- command id: `prod-order-drill-20260722T013656Z`
- command type: `PRODUCTION_ORDER_INTENT`
- command status: `CREATED_NOT_EXECUTABLE`
- worker executable: false
- pre worker executable count: 0
- post worker executable count: 0

## Checks

- insert_succeeded: PASS
- inserted_type_matches: PASS
- inserted_status_non_executable: PASS
- worker_executable_false: PASS
- attempt_zero: PASS
- command_creation_only_true: PASS
- production_signing_executed_false: PASS
- production_http_network_executed_false: PASS
- production_request_sent_false: PASS
- worker_executable_count_unchanged: PASS

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

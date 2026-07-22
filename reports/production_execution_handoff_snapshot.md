# Production Execution Handoff Snapshot

Generated at: `2026-07-22T08:55:33Z`

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
- send executor skeleton: PASS
- send executor execute failure code: PRODUCTION_HTTP_TRANSPORT_NOT_AUTHORIZED
- HTTP transport wiring: PASS
- HTTP transport default failure code: PRODUCTION_HTTP_TRANSPORT_NOT_AUTHORIZED
- HTTP transport fake terminal type: PRODUCTION_HTTP_RESPONSE
- HTTP transport fake external status: FILLED
- request-send gate: PASS
- request-send current template authorized: false
- request-send fixture authorized: true
- send decision entrypoint: PASS
- send decision current template ready: false
- send decision authorized fixture ready: true
- gated executor entrypoint: PASS
- gated executor current template failure code: PRODUCTION_REQUEST_SEND_GATE_CLOSED
- gated executor fake transport external status: FILLED
- credential loader: PASS
- credential loader default code: PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED
- real credential file read: NO
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
- production_send_executor_skeleton_ready: PASS
- production_http_transport_not_authorized_by_default: PASS
- production_http_transport_wiring_ready: PASS
- production_http_transport_fake_response_parsed: PASS
- production_request_send_gate_ready: PASS
- production_request_send_gate_template_closed: PASS
- production_request_send_gate_fixture_authorizes: PASS
- production_send_decision_entrypoint_ready: PASS
- production_send_decision_current_template_blocked: PASS
- production_send_decision_authorized_fixture_ready: PASS
- gated_production_send_executor_entrypoint_ready: PASS
- gated_executor_current_template_closed: PASS
- gated_executor_fake_transport_ready: PASS
- production_credential_loader_ready: PASS
- production_credential_loader_default_closed: PASS

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

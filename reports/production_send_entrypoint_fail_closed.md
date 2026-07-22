# Production Send Entrypoint Fail-Closed Check

Generated at: `2026-07-22T01:29:49Z`

## Result

- result: PASS
- surface: `POST /trade-gate/production-order-intents`
- entrypoint present: true
- valid shape accepted by validator: true
- send authorized: false
- execution gate authorized: false
- current gate config authorized: false
- command creation candidate: true
- command type: `PRODUCTION_ORDER_INTENT`
- non-executable persistence status: `CREATED_NOT_EXECUTABLE`
- worker executable: false
- command created: false
- production request sent: false

## Checks

- valid_shape_accepted_by_validator: PASS
- unbounded_notional_rejected: PASS
- wrong_idempotency_key_rejected: PASS
- secret_field_rejected: PASS
- blocked_response_has_no_command_id: PASS
- default_gate_closed: PASS
- current_gate_config_loaded_and_closed: PASS
- complete_gate_config_can_authorize_command_creation_decision: PASS
- authorized_gate_produces_non_send_command_creation_candidate: PASS

## Boundary

- secret read: NO
- secret value disclosed: NO
- production signing executed: NO
- Authorization header generated: NO
- DNS lookup performed: NO
- socket opened: NO
- production HTTP/network executed: NO
- production request sent: NO
- go-live: NO-GO
- live trading: NO-GO

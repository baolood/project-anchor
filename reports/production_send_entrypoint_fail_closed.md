# Production Send Entrypoint Fail-Closed Check

Generated at: `2026-07-21T10:43:32Z`

## Result

- result: PASS
- surface: `POST /trade-gate/production-order-intents`
- entrypoint present: true
- valid shape accepted by validator: true
- send authorized: false
- command created: false
- production request sent: false

## Checks

- valid_shape_accepted_by_validator: PASS
- unbounded_notional_rejected: PASS
- wrong_idempotency_key_rejected: PASS
- secret_field_rejected: PASS
- blocked_response_has_no_command_id: PASS

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

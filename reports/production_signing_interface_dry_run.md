# Production Signing Interface Dry Run

Generated at: `2026-07-21T07:24:43Z`

## Result

- result: PASS
- signing interface shape valid: true
- missing secret fail-closed: true
- real signing executed: false
- Authorization header generated: false
- signed payload sendable: false

## Validation Checks

- unsigned_canonical_payload_report_pass: PASS
- unsigned_payload_not_sendable: PASS
- signing_readiness_report_pass: PASS
- signing_fields_present_valid: PASS
- signing_input_shape_valid: PASS
- missing_secret_fails_closed: PASS
- authorization_header_not_generated: PASS
- signature_not_generated: PASS

## Signing Field Checks

- PRODUCTION_SIGNING_ALGORITHM: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_SIGNING_CANONICAL_PAYLOAD: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_SIGNING_FAILURE_CLOSED_PATH: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_SIGNING_IDEMPOTENCY_BINDING: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_SIGNING_LOG_REDACTION: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_SIGNING_SECRET_INPUT_BOUNDARY: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_SIGNING_TIMESTAMP_SOURCE: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)

## Signing Input Shape

- execution_mode: production
- market: binance_spot
- symbol: BTCUSDT
- side: BUY
- notional: 4
- order_type: market
- canonical_payload_json_present: True
- idempotency_binding: required_unique_key_per_authorized_window

## Fail-Closed Output Shape

- status: NOT_EXECUTED
- failure_family: PRODUCTION_SIGNING_SECRET_NOT_PROVIDED
- failure_reason: production_signing_secret_not_provided
- material_id: None
- authorization_header_value: None
- signature_value: None
- signed_payload_sendable: False
- network_sent: False
- external_order_id: None
- external_order_id_present: False

## Errors

- none

## Boundary

- secret read: NO
- secret value disclosed: NO
- production signing executed: NO
- Authorization header generated: NO
- signed payload sendable: NO
- DNS lookup performed: NO
- socket opened: NO
- production HTTP/network executed: NO
- production request sent: NO
- canary rerun: NO
- runtime modified: NO
- go-live: NO-GO
- live trading: NO-GO

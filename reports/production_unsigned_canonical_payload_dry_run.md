# Production Unsigned Canonical Payload Dry Run

Generated at: `2026-07-19T15:14:54Z`

## Result

- result: PASS
- unsigned canonical payload generated: true
- sendable: false

## Validation Checks

- risk_limits_source_loaded: PASS
- signing_readiness_pass: PASS
- no_send_drill_pass: PASS
- no_send_authorized_to_execute_false: PASS
- canonical_payload_fields_present: PASS

## Canonical Payload

- execution_mode: production
- market: binance_spot
- symbol: BTCUSDT
- side: BUY
- notional: 4
- order_type: market
- idempotency_key_policy: required_unique_key_per_authorized_window
- max_order_count: 1
- kill_switch_precondition: must_be_false_before_execution
- stop_conditions: any_error_or_unexpected_status_or_duplicate_attempt_stops_execution
- monitoring_window: 15_minutes_after_execution

## Canonical Payload JSON

```json
{"execution_mode":"production","idempotency_key_policy":"required_unique_key_per_authorized_window","kill_switch_precondition":"must_be_false_before_execution","market":"binance_spot","max_order_count":"1","monitoring_window":"15_minutes_after_execution","notional":"4","order_type":"market","side":"BUY","stop_conditions":"any_error_or_unexpected_status_or_duplicate_attempt_stops_execution","symbol":"BTCUSDT"}
```

## Omitted By Design

- api_key
- api_secret
- key_id
- signature
- authorization_header
- timestamp_signature_material
- network_endpoint_probe

## Errors

- none

## Boundary

- secret read: NO
- secret value disclosed: NO
- production signing executed: NO
- Authorization header generated: NO
- DNS lookup performed: NO
- socket opened: NO
- production HTTP/network executed: NO
- production request sent: NO
- canary rerun: NO
- runtime modified: NO
- go-live: NO-GO
- live trading: NO-GO

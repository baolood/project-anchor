# Production HTTP Request Interface Dry Run

Generated at: `2026-07-21T09:29:16Z`

## Result

- result: PASS
- request envelope shape valid: true
- missing Authorization fail-closed: true
- HTTP/network executed: false
- request sent: false

## Validation Checks

- signing_interface_report_pass: PASS
- signing_output_not_sendable: PASS
- authorization_header_missing: PASS
- http_network_readiness_report_pass: PASS
- http_fields_present_valid: PASS
- request_envelope_shape_valid: PASS
- missing_authorization_fails_closed: PASS

## HTTP Field Checks

- PRODUCTION_HTTP_DNS_RESOLUTION_PLAN: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_HTTP_EGRESS_BOUNDARY: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_HTTP_ENDPOINT_ALLOWLIST: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_HTTP_FAILURE_CLOSED_PATH: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_HTTP_IDEMPOTENCY_HEADER: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_HTTP_RESPONSE_REDACTION: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_HTTP_RETRY_POLICY: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)
- PRODUCTION_HTTP_TIMEOUT_POLICY: PASS (actual: PRESENT_VALID, expected: PRESENT_VALID)

## Request Envelope Shape

```json
{
  "body": {
    "execution_mode": "production",
    "idempotency_binding": "required_unique_key_per_authorized_window",
    "market": "binance_spot",
    "notional": "4",
    "order_type": "market",
    "side": "BUY",
    "symbol": "BTCUSDT"
  },
  "execution_mode": "production",
  "headers": {
    "Authorization": null,
    "Content-Type": "application/json",
    "X-Idempotency-Key": null
  },
  "market": "binance_spot",
  "method": "POST",
  "path": "/api/v3/order",
  "sendable": false
}
```

## Fail-Closed Output Shape

- status: NOT_EXECUTED
- failure_family: PRODUCTION_HTTP_AUTHORIZATION_MISSING
- failure_reason: production_http_authorization_missing
- network_sent: False
- dns_lookup_performed: False
- socket_opened: False
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

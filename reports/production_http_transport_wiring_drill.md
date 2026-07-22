# Production HTTP Transport Wiring Drill

Generated at: `2026-07-22T08:02:59Z`

## Result

- result: PASS
- default failure code: PRODUCTION_HTTP_TRANSPORT_NOT_AUTHORIZED
- fake transport called once: true
- fake terminal type: PRODUCTION_HTTP_RESPONSE
- fake external status: FILLED
- fake external order id present: true

## Redacted Requested Payload

- method: POST
- request_path: /api/v3/order
- symbol: BTCUSDT
- side: BUY
- type: MARKET
- quoteOrderQty: 4
- signature_present: True
- api_key_present: True
- sendable: True

## Checks

- transport_not_authorized_by_default: PASS
- fake_transport_called_once: PASS
- fake_transport_response_parsed: PASS
- redaction_preserved: PASS
- real_network_not_used: PASS

## Boundary

- secret read: NO
- secret value disclosed: NO
- production signing with real secret: NO
- Authorization header value disclosed: NO
- DNS lookup performed: NO
- socket opened: NO
- production HTTP/network executed: NO
- production request sent: NO
- canary rerun: NO
- go-live: NO-GO
- live trading: NO-GO

# Production Exactly-One Send Result

Generated at: `2026-07-30T13:52:57Z`

## Result

- result: PASS
- success: true
- failure code: None
- execution requested: true
- readiness result: PASS
- readiness decision: READY_FOR_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_WINDOW_OPEN

## Request

- idempotency key: `production:ops_manual:BTCUSDT:BUY:10:first-bounded-production-request:v1`
- market: binance_spot
- symbol: BTCUSDT
- side: BUY
- max notional: 10
- order type: market

## Execution Host Contract

- expected Binance API IP whitelist: 45.76.190.109
- observed platform: Linux
- compliant: true
- failure code: None

## Credential Contract

- path: `/etc/project-anchor/production.env`
- expected owner: project_anchor_runtime
- expected group: project_anchor_runtime
- expected mode: 600
- stat error: None
- observed owner: project_anchor_runtime
- observed group: project_anchor_runtime
- observed mode: 600
- compliant: true

## Terminal

- terminal type: PRODUCTION_HTTP_RESPONSE
- http status: 200
- external status: FILLED
- external request started: true
- external order id present: true
- exchange error code present: None
- exchange error message present: None
- exchange error code: None
- exchange error message: None
- transport error type: None

## Boundary

- credential file read: YES
- secret value disclosed: NO
- secret length disclosed: NO
- secret prefix/suffix disclosed: NO
- secret hash disclosed: NO
- production signing executed: YES
- Authorization header value disclosed: NO
- DNS lookup or socket possible: YES
- production HTTP/network attempted: YES
- production request attempted: YES
- production request accepted: YES
- canary rerun: NO
- go-live: NO-GO
- live trading: NO-GO

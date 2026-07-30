# Production Exactly-One Send Result

Generated at: `2026-07-30T10:27:38Z`

## Result

- result: BLOCKED
- success: false
- failure code: PRODUCTION_SEND_EXECUTION_NOT_REQUESTED
- execution requested: false
- readiness result: PASS
- readiness decision: READY_FOR_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_WINDOW_OPEN

## Request

- idempotency key: `production:ops_manual:BTCUSDT:BUY:4:first-bounded-production-request:v1`
- market: binance_spot
- symbol: BTCUSDT
- side: BUY
- max notional: 4
- order type: market

## Credential Contract

- path: `/etc/project-anchor/production.env`
- expected owner: project_anchor_runtime
- expected group: project_anchor_runtime
- expected mode: 600
- stat error: PERMISSION_DENIED
- observed owner: None
- observed group: None
- observed mode: None
- compliant: false

## Terminal

- terminal type: None
- http status: None
- external status: None
- external request started: false
- external order id present: false
- exchange error code present: None
- exchange error message present: None
- transport error type: None

## Boundary

- credential file read: NO
- secret value disclosed: NO
- secret length disclosed: NO
- secret prefix/suffix disclosed: NO
- secret hash disclosed: NO
- production signing executed: NO
- Authorization header value disclosed: NO
- DNS lookup or socket possible: NO
- production HTTP/network attempted: NO
- production request attempted: NO
- production request accepted: NO
- canary rerun: NO
- go-live: NO-GO
- live trading: NO-GO

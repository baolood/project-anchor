# Next Manual Low-Frequency Production Send Result

Generated at: `2026-08-05T11:00:56Z`

## Result

- result: BLOCKED
- success: false
- failure code: NEXT_MANUAL_PRODUCTION_SEND_EXECUTION_NOT_REQUESTED
- execution requested: false
- eligibility result: PASS
- eligibility decision: READY_FOR_NEXT_MANUAL_LOW_FREQUENCY_OPERATOR_AUTHORIZATION_DECISION

## Request

- idempotency key: `production:ops_manual:BTCUSDT:BUY:10:next-manual-low-frequency-request:v1`
- market: binance_spot
- symbol: BTCUSDT
- side: BUY
- max notional: 10
- order type: market

## Execution Host Contract

- expected Binance API IP whitelist: 45.76.190.109
- observed platform: Darwin
- compliant: false
- failure code: PRODUCTION_EXECUTION_HOST_NOT_WHITELISTED

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
- exchange error code: None
- exchange error message: None
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
- automatic retry: NO
- second request sent: NO
- canary rerun: NO
- go-live: NO-GO
- live trading: NO-GO

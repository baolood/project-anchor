# Fresh Production Send Readiness Decision

Generated at: `2026-07-22T09:16:55Z`

## Result

- result: PASS
- decision: READY_FOR_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_WINDOW_OPEN
- send authorized by this decision: false
- execution performed by this decision: false

## Risk Limit Summary

- market: binance_spot
- symbols: BTCUSDT
- sides: BUY_ONLY
- max_notional: 4
- max_order_count: 1
- idempotency_policy: required_unique_key_per_authorized_window

## Planned Window

- duration_minutes: 60
- expires_at: 2026-07-22T10:16:55Z
- monitor_until: 2026-07-22T10:31:55Z
- monitoring_window: 15_minutes_after_execution
- not_before: 2026-07-22T09:16:55Z
- window_type: fresh_bounded_authorization_window

## Planned Request

- idempotency_key_template: production:ops_manual:BTCUSDT:BUY:4:first-bounded-production-request:v1
- idempotency_policy: required_unique_key_per_authorized_window
- market: binance_spot
- max_notional: 4
- max_order_count: 1
- order_type: market
- sendable: False
- side: BUY
- symbol: BTCUSDT

## Checks

- handoff_ready_for_decision: PASS (handoff snapshot PASS / READY_FOR_DECISION)
- pre_send_chain_complete: PASS (pre-send aggregation PASS and complete)
- final_runner_ready: PASS (final runner PASS with fail-closed defaults and fake transport evidence)
- window_plan_valid: PASS (send window plan PASS)
- window_plan_not_authorizing: PASS (window plan remains non-authorizing)
- fresh_window_current: PASS (current time is within the latest planned window)
- production_request_not_sent: PASS (all evidence says production request has not been sent)
- risk_limits_bounded: PASS (production risk limits remain exactly-one BTCUSDT BUY max notional 4)
- go_live_still_no_go: PASS (go-live remains NO-GO)
- live_trading_still_no_go: PASS (live trading remains NO-GO)

## Errors

- none

## Boundary

- credential file read: NO
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

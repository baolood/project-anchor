# Production Request Send Window Plan

Generated at: `2026-07-22T08:30:29Z`

## Result

- result: PASS
- plan valid: true
- send authorized: false
- execution allowed by this plan: false
- next gate: WAITING_FOR_EXPLICIT_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_AUTHORIZATION

## Planned Window

- window_type: fresh_bounded_authorization_window
- not_before: 2026-07-22T08:30:29Z
- expires_at: 2026-07-22T09:30:29Z
- duration_minutes: 60
- monitor_until: 2026-07-22T09:45:29Z
- monitoring_window: 15_minutes_after_execution

## Planned Request

- market: binance_spot
- symbol: BTCUSDT
- side: BUY
- max_notional: 4
- max_order_count: 1
- order_type: market
- idempotency_policy: required_unique_key_per_authorized_window
- idempotency_key_template: production:ops_manual:BTCUSDT:BUY:4:first-bounded-production-request:v1
- sendable: False

## Preconditions

- kill_switch: must_be_false_before_execution
- pre_send_evidence_chain_complete: True
- operator_must_provide_explicit_send_authorization: True
- no_retry: True
- exactly_one_request_only: True

## Stop Conditions

- policy: any_error_or_unexpected_status_or_duplicate_attempt_stops_execution
- stop_on_any_error: True
- stop_on_unexpected_status: True
- stop_on_duplicate_attempt: True
- stop_on_scope_drift: True
- stop_on_secret_disclosure_risk: True

## Validation Checks

- pre_send_evidence_chain_complete: PASS (pre-send aggregation PASS and complete)
- pre_send_does_not_authorize_send: PASS (pre-send evidence remains non-authorizing)
- market_present: PASS (production market present)
- symbol_present: PASS (production symbol present)
- side_bounded: PASS (production side bounded)
- max_notional_present: PASS (max notional present)
- max_order_count_one: PASS (max order count is one)
- idempotency_policy_present: PASS (idempotency policy present)
- kill_switch_precondition_present: PASS (kill-switch precondition present)
- stop_conditions_present: PASS (stop conditions present)
- monitoring_window_present: PASS (monitoring window present)

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

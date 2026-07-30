# Post Production Send Reconciliation

Generated at: `2026-07-30T14:02:53Z`

## Result

- result: PASS
- next gate: POST_PRODUCTION_SEND_MONITORING_AND_BALANCE_RECONCILIATION

## Summary

- production_send_result: PASS
- production_send_success: True
- production_request_attempted: YES
- production_request_accepted: YES
- http_status: 200
- external_status: FILLED
- external_order_id_present: True
- idempotency_key: production:ops_manual:BTCUSDT:BUY:10:first-bounded-production-request:v1
- symbol: BTCUSDT
- side: BUY
- max_notional: 10

## Checks

- send_result_pass: PASS (send report result is PASS)
- production_request_attempted: PASS (production request was attempted exactly by the send report)
- production_request_accepted: PASS (production request was accepted)
- http_200: PASS (terminal HTTP status is 200)
- terminal_filled: PASS (terminal external status is FILLED)
- external_order_id_present: PASS (external order id presence is true)
- idempotency_key_matches_risk_limit: PASS (idempotency key matches current max notional risk limit)
- window_plan_pass: PASS (send window plan is PASS)
- fresh_decision_pass: PASS (fresh send readiness decision was PASS)
- window_plan_did_not_authorize_send: PASS (window plan remains non-authorizing)
- fresh_decision_did_not_authorize_send: PASS (fresh readiness decision remains non-authorizing)
- bounded_symbol: PASS (symbol is BTCUSDT)
- bounded_side: PASS (side is BUY)
- bounded_notional: PASS (max notional is 10)
- exactly_one_order_count: PASS (max order count is one)
- no_secret_disclosure: PASS (secret values, lengths, prefixes/suffixes, and hashes were not disclosed)
- authorization_header_not_disclosed: PASS (Authorization header value was not disclosed)
- no_canary_rerun: PASS (canary was not rerun)
- go_live_no_go: PASS (go-live remains NO-GO)
- live_trading_no_go: PASS (live trading remains NO-GO)

## Errors

- none

## Boundary

- secret_value_disclosed: NO
- secret_length_disclosed: NO
- secret_prefix_suffix_disclosed: NO
- secret_hash_disclosed: NO
- authorization_header_value_disclosed: NO
- new_production_request_sent_by_reconciliation: NO
- second_production_request_sent: NO
- retry_performed: NO
- canary_rerun: NO
- go_live: NO-GO
- live_trading: NO-GO

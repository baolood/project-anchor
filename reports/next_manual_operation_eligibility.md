# Next Manual Operation Eligibility

Generated at: `2026-08-05T09:48:59Z`

## Result

- result: PASS
- decision: READY_FOR_NEXT_MANUAL_LOW_FREQUENCY_OPERATOR_AUTHORIZATION_DECISION
- next single task: operator_decision_for_next_manual_low_frequency_operation

## Policy

- market: binance_spot
- symbols: ['BTCUSDT']
- sides: ['BUY_ONLY']
- max_notional_per_request: 10
- max_order_count_per_request: 1
- minimum_hours_between_production_requests: 24
- recommended_max_requests_per_week: 3
- explicit_operator_authorization_required: True

## Eligibility

- last_production_request_at: 2026-07-30T13:52:57Z
- next_eligible_at: 2026-07-31T13:52:57Z
- hours_since_last_production_request: 139.93
- observed_production_requests_last_7d: 1
- eligible_for_operator_authorization_decision: YES
- production_send_authorization_granted: NO

## Evidence

- last_production_send_result: PASS
- last_production_send_external_status: FILLED
- external_order_reference_present: True
- post_send_reconciliation: PASS
- post_production_72h_stability: PASS
- post_production_monitoring: PASS
- telegram_channel_delivery: PASS

## Checks

- policy_manual_low_frequency: PASS
- operator_authorization_required: PASS
- automatic_retry_disabled: PASS
- automatic_trading_disabled: PASS
- go_live_disabled: PASS
- live_trading_disabled: PASS
- last_production_send_pass: PASS
- last_production_send_filled: PASS
- last_production_send_timestamp_present: PASS
- minimum_interval_satisfied: PASS
- weekly_recommended_limit_not_reached: PASS
- post_send_reconciliation_pass: PASS
- post_production_72h_stability_pass: PASS
- post_production_monitoring_pass: PASS
- telegram_channel_delivery_confirmed: PASS

## Blockers

- none

## Boundary

- secret_read: NO
- credential_file_read: NO
- production_signing_executed: NO
- production_http_network_attempted: NO
- production_request_sent: NO
- second_production_request_sent: NO
- canary_rerun: NO
- go_live: NO-GO
- live_trading: NO-GO

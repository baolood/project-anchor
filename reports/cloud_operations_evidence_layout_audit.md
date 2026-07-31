# Cloud Operations Evidence Layout Audit

Generated at: `2026-07-31T05:35:28Z`

## Result

- result: PASS
- status: CLOUD_OPERATIONS_EVIDENCE_LAYOUT_VALID
- runtime reports dir: `/var/lib/project-anchor/reports`
- source reports dir: `/root/project-anchor/reports`
- single directory layout required: NO

## Runtime Reports

- post_production_monitoring_run.json: PRESENT
- post_production_monitoring_timer_runtime_validation.json: PRESENT
- post_production_monitoring_timer_stability_validation.json: PRESENT
- post_production_monitoring_telegram_send_result.json: PRESENT

## Source Evidence Reports

- production_exactly_one_send_result.json: PRESENT
- post_production_send_reconciliation.json: PRESENT
- production_post_send_readonly_reconciliation.json: PRESENT
- post_production_operations_decision.json: PRESENT

## Summary

- monitoring_generated_at: 2026-07-31T05:24:41Z
- monitoring_result: PASS
- timer_runtime_result: PASS
- timer_stability_result: PASS
- timer_consecutive_successes: 6
- telegram_sender_result: BLOCKED
- production_send_result: PASS
- production_order_status: FILLED
- matching_filled_order_count: 1
- symbol_order_count_in_window: 1
- operations_decision: FIRST_PRODUCTION_VALIDATION_COMPLETE_CONTINUOUS_TRADING_DISABLED

## Checks

- runtime_monitoring_reports_present: PASS
- source_production_evidence_present: PASS
- monitoring_run_pass: PASS
- timer_runtime_pass: PASS
- timer_stability_pass: PASS
- telegram_sender_fail_closed_or_delivered: PASS
- production_send_pass: PASS
- production_terminal_filled: PASS
- readonly_reconciliation_pass: PASS
- exactly_one_matching_order: PASS
- operations_decision_pass: PASS
- decision_records_single_production_request: PASS
- no_new_request_from_monitoring: PASS
- no_second_request_from_monitoring: PASS
- go_live_no_go: PASS
- live_trading_no_go: PASS

## Boundary

- production_env_read: NO
- secret_value_disclosed: NO
- production_signing_executed: NO
- production_http_network_attempted: NO
- new_production_request_sent: NO
- second_production_request_sent: NO
- canary_rerun: NO
- go_live: NO-GO
- live_trading: NO-GO

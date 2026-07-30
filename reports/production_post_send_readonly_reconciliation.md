# Production Post-Send Read-Only Reconciliation

Generated at: `2026-07-30T14:20:33Z`

## Result

- result: PASS
- next gate: POST_PRODUCTION_SEND_OPERATIONS_DECISION

## Order Reconciliation

- orders returned: 1
- matching FILLED order count: 1
- BTCUSDT order count in window: 1
- matching order present: true

## Account Reconciliation

- account payload visible: true
- USDT balance row present: true
- BTC balance row present: true
- balance amounts recorded: NO

## Checks

- send_report_pass: PASS (stored production send report is PASS)
- stored_terminal_filled: PASS (stored terminal external status is FILLED)
- readonly_queries_attempted: PASS (read-only order and account queries were attempted)
- order_query_ok: PASS (allOrders read-only query returned a list)
- account_query_ok: PASS (account read-only query returned an object)
- matching_filled_order_count_one: PASS (exactly one matching FILLED BTCUSDT BUY market order found)
- no_second_symbol_order_in_window: PASS (exactly one BTCUSDT order found in the authorized window)
- usdt_balance_visible: PASS (USDT balance row is visible without recording amount)
- btc_balance_visible: PASS (BTC balance row is visible without recording amount)

## Errors

- none

## Boundary

- credential_file_read: YES
- secret_value_disclosed: NO
- secret_length_disclosed: NO
- secret_prefix_suffix_disclosed: NO
- secret_hash_disclosed: NO
- authorization_header_value_disclosed: NO
- read_only_order_query_attempted: YES
- read_only_account_query_attempted: YES
- production_order_sent: NO
- second_production_request_sent: NO
- retry_performed: NO
- canary_rerun: NO
- go_live: NO-GO
- live_trading: NO-GO

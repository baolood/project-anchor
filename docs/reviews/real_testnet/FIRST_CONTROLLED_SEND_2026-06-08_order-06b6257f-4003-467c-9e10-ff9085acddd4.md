# First Controlled Send Actual Artifact

review_date: 2026-06-08
reviewer: baolood
operator: baolood
host_label: binance_futures_testnet
configured_origin: https://demo-fapi.binance.com
runtime_posture: canonical_testnet_real
executor_mode: real
command_id: order-06b6257f-4003-467c-9e10-ff9085acddd4
idempotency_key: testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1
final_result_label: PASS
final_command_state: DONE
normalized_family: canonical_real_testnet_filled_success
external_request_status: accepted
external_status: FILLED
external_order_id: 14467233803
retreat_required: no
notes: The bounded cloud-host event remained on the canonical ORDER:testnet path, used persistent canonical TESTNET_* runtime wiring, reached Binance Demo/Testnet, and returned one reviewable filled result without a second request. This artifact proves a real non-synthetic first controlled send event exists while canary, go-live, and live trading remain closed.

## Path Identity

- command type: `ORDER`
- payload.execution_mode: `testnet`
- canonical_path: `ORDER:testnet`
- market: `binance_testnet`
- source: `ops_manual`

## Runtime Posture

- host runtime aligned to canonical `TESTNET_*`
- `TESTNET_EXECUTOR_MODE=real`
- `TESTNET_EXECUTOR_REAL_ENABLE=1`
- configured origin: `https://demo-fapi.binance.com`
- credential material for canonical `TESTNET_*` present at review time
- `TESTNET_EXCHANGE_KEY_ID` present
- `kill_switch_enabled=false`
- `telegram_enabled=true`

## Command Payload Summary

- symbol: `BTCUSDT`
- side: `BUY`
- notional: `4.0`
- order_type: `market`
- stop_price: `68000`
- created_by: `baolood`

## Command Detail Facts

- status: `DONE`
- attempt: `1`
- execution_mode: `testnet`
- host_label: `binance_futures_testnet`
- configured_origin: `https://demo-fapi.binance.com`
- external_request_started: `true`
- external_order_id_present: `true`
- external_status: `FILLED`
- external_order_id: `14467233803`

## Event Chain

1. bounded operator window authorized
2. hardened precheck passed inside valid window
3. `POST /trade-gate/testnet-order-intents` accepted
4. worker picked the command
5. external Binance Demo/Testnet request started
6. external result returned `FILLED`
7. command marked `DONE`

## Review Conclusion

This bounded cloud-host event is non-synthetic and reviewable. It proves that the canonical `ORDER + execution_mode=testnet` path can complete one real external Binance Demo/Testnet request and produce one filled result with an external order id. The event remained bounded to one canonical request. Canary remains `NOT AUTHORIZED`, go-live remains `NO-GO`, and live trading remains `NO-GO`.

# Exactly-One Bounded Real Testnet Send HTTP 451 Closeout V1

## Scope

Record the authorized exactly-one bounded real external testnet send result for Project Anchor.

This closeout does not authorize a retry, canary, live trading, or production go-live.

## Authorization And Window

- operator decision: GRANTED
- authorization timestamp: 2026-07-01T17:53:35+08:00
- window start: 2026-07-01T18:03:35+08:00
- window end: 2026-07-01T18:53:35+08:00
- send time observed: 2026-07-01T18:09:56+08:00 / 2026-07-01T10:09:56Z
- window status at send: INSIDE_WINDOW
- sent inside window: YES

## Pre-Send Checks

- workspace guard: PASS
- git status clean before send: YES
- hardened one-shot guardrail: PASS
- go-live rules: PASS
- local box baseline: PASS
- docker compose services: backend/postgres/redis/worker all Up
- backend /health: PASS
- /ops/state: PASS
- kill switch enabled: false
- worker available: YES
- testnet credential runtime presence: PASS by name/status only
- secret values printed: NO

## Send Result

- local intent endpoint POST: SENT
- exactly one local request: YES
- command_id: order-cdf35b49-bc0a-4999-af9b-4e54fb333a61
- idempotency key: testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1
- automatic retry: NO
- result: FAILED
- failure gate: external_executor
- failure family: TESTNET_EXECUTOR_UNEXPECTED
- failure reason: http_451_restricted_location
- http status: 451

## External Exchange Boundary

- upstream external exchange request: STARTED
- upstream external exchange request started: YES
- host label: binance_futures_testnet
- configured origin: https://demo-fapi.binance.com
- execution mode: testnet
- executor mode label: real
- timeout policy label: single_attempt_v1
- external_order_id: N/A
- external_order_id_present: false

The command was accepted by the local testnet intent endpoint, picked by the worker, allowed by policy, checked against the kill switch, and handed to the testnet executor. The upstream testnet endpoint rejected the request with HTTP 451 restricted-location response before any external order id was created.

## Event Chain

PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_REJECTED -> ACTION_FAIL -> MARK_FAILED

## Evidence

- command detail endpoint: GET /domain-commands/order-cdf35b49-bc0a-4999-af9b-4e54fb333a61
- command events endpoint: GET /domain-commands/order-cdf35b49-bc0a-4999-af9b-4e54fb333a61/events
- worker log summary: mark FAILED with TESTNET_EXECUTOR_UNEXPECTED, http_status 451, external_request_started true, external_order_id_present false
- /ops/state after send: PASS, kill switch enabled false, worker heartbeat fresh
- closeout recorded at: 2026-07-01T10:12:04Z

## Final State

- current blocker: TESTNET_UPSTREAM_RESTRICTED_LOCATION_AFTER_BOUNDED_REAL_SEND
- real external testnet request: STARTED_AND_REJECTED
- local intent endpoint POST: SENT
- upstream external exchange request: STARTED
- external order id present: false
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

## Next Action

Stop and review.

Do not retry this request. Do not open canary or go-live from this closeout. Any future action must be a separate operator-authorized decision about the restricted-location blocker and must preserve the no-retry fact for this bounded send.

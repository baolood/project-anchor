# Exactly-One Simulator Failed Send Prep V1

## 1. Purpose

- prepare the next safe step after the REJECTED closeout merge
- document the exact operator plan for one future simulator FAILED send
- no simulator request execution in this task
- no real external exchange request

This document is preparation only. It does not authorize or execute the FAILED scenario.

## 2. Current State

- REJECTED closeout merged: YES
- REJECTED closeout merge commit: `06f5c9e89d711cae894b23fcc8983fd3f9a748ce`
- current safe status: `READY_FOR_EXACTLY_ONE_SIMULATOR_FAILED_SEND_PREP`
- FAILED scenario executed: NO
- simulator request executed after REJECTED closeout: NO
- real external exchange request sent: NO
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

## 3. Future FAILED Send Boundary

The future FAILED send must be a separate bounded task.

- exactly one simulator request
- scenario: FAILED
- idempotency key: `simulator:ops_manual:BTCUSDT:BUY:4:first-failed:v1`
- market: `binance_testnet`
- symbol: `BTCUSDT`
- side: `BUY`
- notional: `4.0`
- execution mode: `simulator`
- source: `ops_manual`
- created_by: `operator`
- no real external exchange request
- no canary
- live trading: NO-GO
- go-live: NO-GO

## 4. Required Preflight Before Future Send

- workspace guard PASS
- local branch is `main`
- local main synced with origin
- git status clean
- simulator tests PASS
- hardened one-shot guardrail PASS
- go-live rules PASS
- local box baseline PASS
- backend `/health` PASS if runtime is used
- `/ops/state` PASS if runtime is used
- kill switch false if runtime is used
- worker available if command lifecycle is used

## 5. Expected Future Evidence

After the future FAILED send, the closeout must record:

- exactly one simulator request recorded
- command_id
- idempotency key
- scenario: FAILED
- result: FAILED
- terminal event: `TESTNET_EXECUTOR_FAILED`
- failure_family: `TESTNET_EXECUTOR_SIMULATOR_FAILED`
- failure reason present
- external_request_started: true
- simulator_order_id / external_order_id equivalent present: NO
- event chain includes `TESTNET_EXECUTOR_REQUESTED`
- event chain includes `TESTNET_EXECUTOR_FAILED`
- event chain includes `MARK_FAILED` or lifecycle equivalent
- duplicate request sent: NO
- real external exchange request sent: NO
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

## 6. Stop Conditions

- wrong workspace
- branch is not `main`
- git status is not clean
- validation fails
- runtime unavailable if runtime path is used
- kill switch enabled
- scenario differs from FAILED
- more than one simulator request would be sent
- simulator_order_id / external_order_id equivalent would be present
- real external exchange request would be sent
- canary or live/go-live path would be touched

## 7. Next Safe Status

- `READY_FOR_EXACTLY_ONE_SIMULATOR_FAILED_SEND_AUTHORIZATION`

This prep keeps go-live blocked. It does not authorize FAILED execution, additional simulator requests, real exchange requests, canary, live trading, go-live, runtime changes, credential changes, backend changes, worker changes, risk changes, deploy changes, migrations, Docker changes, compose changes, or frontend changes.

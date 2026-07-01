# Simulator Rejected Failed Matrix Prep V1

## 1. Purpose

- prepare the next simulator matrix scenarios after the accepted send closeout
- no simulator request execution in this task
- no real external exchange request

This document fixes the preparation boundary for the REJECTED and FAILED simulator scenarios. It does not execute either scenario and does not authorize any additional request.

## 2. Current State

- accepted simulator send closeout in main: YES
- exactly one accepted simulator request recorded: YES
- accepted simulator_order_id recorded: YES
- next scenarios requiring preparation: REJECTED / FAILED
- additional simulator request executed by this prep: NO
- real external exchange request sent: NO
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

## 3. Matrix Scope

### REJECTED Scenario

- scenario: `rejected`
- expected terminal event: `TESTNET_EXECUTOR_REJECTED`
- expected command final state: `FAILED`
- expected simulator_order_id / external_order_id equivalent: absent
- expected failure_family: `TESTNET_EXECUTOR_REJECTED`
- expected external_request_started: true
- expected lifecycle: `PICKED -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_REJECTED -> ACTION_FAIL -> MARK_FAILED`

### FAILED Scenario

- scenario: `failed`
- expected terminal event: `TESTNET_EXECUTOR_FAILED`
- expected command final state: `FAILED`
- expected simulator_order_id / external_order_id equivalent: absent
- expected failure_family: `TESTNET_EXECUTOR_SIMULATOR_FAILED`
- expected external_request_started: true
- expected lifecycle: `PICKED -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_FAILED -> ACTION_FAIL -> MARK_FAILED`

## 4. Required Input

Both future scenario executions must use project-approved simulator routing only.

- market: `binance_testnet`
- symbol: `BTCUSDT`
- side: `BUY`
- notional: `4.0`
- execution mode: `simulator`
- source: `ops_manual`
- created_by: `operator`
- REJECTED idempotency key: `simulator:ops_manual:BTCUSDT:BUY:4:first-rejected:v1`
- FAILED idempotency key: `simulator:ops_manual:BTCUSDT:BUY:4:first-failed:v1`

Each future scenario must be executed and closed out as a separate bounded task unless the operator explicitly authorizes a combined matrix execution. This prep does not provide that authorization.

## 5. Required Preflight Before Any Future Scenario

- workspace guard PASS
- main clean
- simulator tests PASS
- hardened one-shot guardrail PASS
- go-live rules PASS
- local box baseline PASS
- backend `/health` PASS if runtime is used
- `/ops/state` PASS if runtime is used
- kill switch false if runtime is used
- worker available if command lifecycle is used

## 6. Stop Conditions

- wrong workspace
- git status not clean
- validation fails
- runtime unavailable if runtime path is used
- kill switch enabled
- scenario differs from the authorized scenario
- simulator_order_id or external_order_id equivalent appears on REJECTED or FAILED
- terminal event does not match the authorized scenario
- more than one request would be sent for a scenario
- real external exchange request would be sent

## 7. Closeout Requirement

Each future scenario closeout must record:

- command_id
- idempotency key
- scenario
- result
- terminal event
- failure_family
- external_request_started
- simulator_order_id / external_order_id equivalent absent
- event chain
- exactly one simulator request for that scenario
- duplicate not sent
- real external exchange request NOT SENT
- canary NOT EXECUTED
- live trading NO-GO
- go-live NO-GO

## 8. Next Safe Status

- `READY_FOR_EXACTLY_ONE_SIMULATOR_REJECTED_SEND_PREP`
- `READY_FOR_EXACTLY_ONE_SIMULATOR_FAILED_SEND_PREP`

This prep does not authorize REJECTED execution, FAILED execution, additional simulator requests, real exchange requests, canary, live trading, go-live, runtime changes, or credential changes.

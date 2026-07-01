# Exactly-One Simulator Send Prep V1

## 1. Purpose

- prepare first exactly-one simulator send
- no execution in this task

This document prepares the first controlled simulator send after the minimal simulator implementation and closeout were merged into main. It is a preparation record only.

## 2. Scope

- simulator only
- no real external exchange request
- no Binance retry
- no canary
- no live trading
- go-live remains NO-GO

## 3. Scenario

- first simulator send should use ACCEPTED path
- must return `simulator_order_id` or external_order_id equivalent
- must verify `REQUESTED -> ACCEPTED -> MARK_DONE` or equivalent existing lifecycle

## 4. Required Input

- market: existing project-approved simulator market value
- symbol: `BTCUSDT`
- side: `BUY`
- notional: `4.0`
- idempotency key: `simulator:ops_manual:BTCUSDT:BUY:4:first-accepted:v1`
- execution mode: `simulator`
- source: `ops_manual`
- created_by: `operator`

The implementation currently validates the simulator helper through the existing testnet executor path. The exact runtime command shape must be selected in the separate send task, using only project-approved simulator routing.

## 5. Preflight

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

- git status not clean
- validation fails
- runtime unavailable if runtime path is used
- kill switch enabled
- `simulator_order_id` absent on ACCEPTED path
- more than one request would be sent

## 7. Closeout Requirement

The send closeout must record:

- command_id
- idempotency key
- scenario
- result
- simulator_order_id / external_order_id equivalent
- event chain
- duplicate not sent
- canary NOT EXECUTED
- live trading NO-GO
- go-live NO-GO

## 8. Next Safe Status

- `READY_FOR_EXACTLY_ONE_SIMULATOR_ACCEPTED_SEND`

This prep does not authorize real exchange requests, Binance retry, canary, live trading, go-live, runtime changes, credential changes, or a second simulator send.

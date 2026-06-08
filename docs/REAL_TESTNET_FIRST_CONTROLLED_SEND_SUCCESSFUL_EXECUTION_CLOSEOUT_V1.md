# Real testnet first controlled send successful execution closeout V1

**Status:** successful bounded testnet execution closeout - one real external testnet request sent and filled; canary not authorized; go-live remains NO-GO; live trading remains NO-GO.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-06-08**

**Scope:** close the first bounded controlled real external testnet send after the canonical `ORDER + execution_mode=testnet` path completed one real external request and returned a reviewable filled result.

This document does not authorize canary execution, production launch, or live trading.
It closes one bounded testnet execution window only.

## 1. Decision

The first bounded controlled real external testnet send is now **PASS** as a bounded execution event.

At this point, the main remaining blocker is no longer:

```text
whether the canonical ORDER:testnet path can reach
the external executor and finish with one reviewable result
```

The correct new interpretation is:

```text
the canonical bounded testnet execution chain has now been proven once,
with one real external request, one reviewable command result,
and one external order id returned from Binance Demo/Testnet
```

## 2. Window identity

- `authorization_timestamp`: `2026-06-08T09:20:26+08:00`
- `window_start`: `2026-06-08T09:30:26+08:00`
- `window_end`: `2026-06-08T09:45:26+08:00`
- `operator`: `baolood`
- `target_environment`: `stage / bounded testnet environment only`
- `invocation_surface`: `POST /trade-gate/testnet-order-intents`
- `request_family`: `canonical ORDER + execution_mode=testnet exact invocation packet path`

## 3. Preconditions at open

The bounded execution window opened under the expected posture:

- `/health`: `PASS`
- `/ops/state`: `PASS`
- `/ops/worker`: `PASS`
- `kill_switch_enabled`: `false`
- `worker_heartbeat`: `PASS`
- `telegram_enabled`: `true`
- `TESTNET_EXCHANGE_BASE_URL`: `https://demo-fapi.binance.com`
- `TESTNET_EXCHANGE_API_KEY`: present
- `TESTNET_EXCHANGE_API_SECRET`: present
- `TESTNET_EXCHANGE_KEY_ID`: present
- `TESTNET_EXECUTOR_MODE`: `real`
- `TESTNET_EXECUTOR_REAL_ENABLE`: `1`

The hardened one-shot precheck passed inside the valid window before execution.

## 4. Attempt facts

Exactly one bounded request was attempted.

- `request_attempted`: `YES`
- `command_id`: `order-06b6257f-4003-467c-9e10-ff9085acddd4`
- `idempotency_key`: `testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1`
- `market`: `binance_testnet`
- `symbol`: `BTCUSDT`
- `side`: `BUY`
- `notional`: `4.0`
- `order_type`: `market`
- `created_by`: `baolood`

No second request was attempted in this bounded round.

## 5. Execution outcome

The canonical execution path produced one reviewable success result:

- `final_command_state`: `DONE`
- `attempt`: `1`
- `execution_mode`: `testnet`
- `external_status`: `FILLED`
- `external_order_id`: `14467233803`

This means the request was not only accepted by the external executor, but completed with a returned exchange order id and filled status.

## 6. Boundary interpretation

The correct boundary statement for this event is:

- `POST executed`: `YES, exactly once`
- `real external request sent`: `YES`
- `external order id present`: `YES`
- `canary`: `NOT AUTHORIZED`
- `go-live`: `NO-GO`
- `live trading`: `NO-GO`

This closeout is a bounded testnet proof only.
It must not be interpreted as permission to start canary, production launch, or live trading.

## 7. What was proven

This event proves all of the following together:

1. the canonical backend route can accept the bounded operator request
2. the worker can pick up the resulting command
3. the persistent `/etc/project-anchor/testnet.env` wiring is sufficient for real testnet execution
4. the canonical `demo-fapi` origin is accepted by the host-safety boundary
5. the Binance Demo/Testnet credentials path is valid enough to produce one filled external result
6. the hardened one-shot guard can still constrain the event to one bounded request

That is the first real non-synthetic proof of the complete bounded testnet execution chain.

## 8. Remaining limits

Even with this `PASS`, the following remain true:

- this was one bounded testnet execution only
- no canary execution is authorized by this closeout
- no go-live decision is implied by this closeout
- no live trading authorization exists
- any future external request still requires its own fresh timing, operator authorization, precheck, and bounded execution review

## 9. Final verdict

The correct verdict for this bounded event is:

```text
PASS
```

And the correct stable status statement is:

```text
first bounded controlled real external testnet send:
PASS
one canonical request executed
one real external request sent
one filled result captured
canary: NOT AUTHORIZED
go-live: NO-GO
live trading: NO-GO
```

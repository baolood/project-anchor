# Real External Request Single Command Exact Invocation Packet V1

## 1. Purpose

This artifact fixes one exact operator invocation packet for the first bounded
real external request path after the canonical `ORDER:testnet` endpoint has
been implemented.

It freezes:

- one exact invocation surface
- one exact bounded request body
- one exact idempotency key rule
- one exact evidence capture command set
- one exact blocked-evidence capture command set
- one exact retreat / stop sequence

This packet still does **not** authorize execution by itself.

## 2. Current status

- exact invocation packet prepared: YES
- exact invocation surface fixed: YES
- exact bounded request body fixed: YES
- exact idempotency rule fixed: YES
- exact evidence capture command set fixed: YES
- exact retreat / stop sequence fixed: YES
- final execution command approved now: NO
- real external request authorized now: NO
- real external request sent now: NO
- canary executed now: NO
- go-live: NO-GO
- live trading: NO-GO

## 3. Exact invocation surface

The single approved invocation surface for the first bounded request packet is:

```text
direct backend route on the stage host only
POST http://127.0.0.1:8000/trade-gate/testnet-order-intents
```

This packet does **not** use:

- the console proxy as the execution surface
- `/trade-gate/dry-run-intents`
- `POST /domain-commands/quote`
- generic `POST /commands`
- shell scripts

The console proxy remains implemented and reviewable, but it is **not** the
approved first bounded invocation surface for the first operator-run request
packet.

## 4. Exact bounded request body

The exact bounded request body for the first invocation packet is:

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "notional": 4,
  "stop_price": 68000,
  "order_type": "market",
  "created_by": "baolood",
  "idempotency_key": "testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1"
}
```

Field expectations:

- `symbol` must remain `BTCUSDT`
- `side` must remain `BUY`
- `notional` must remain `4`
- `stop_price` must remain `68000`
- `order_type` must remain `market`
- `created_by` must remain the active operator identity
- `limit_price` must not be sent in this first packet

This packet is therefore:

```text
one market BUY intent
one bounded notional
one fixed stop_price
one fixed operator identity
one fixed idempotency_key
```

## 5. Exact idempotency rule

The idempotency key is not free-form for this packet.

Approved rule:

```text
testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1
```

This value is fixed for the first bounded packet and must not be mutated during
the same authorization window.

If the packet is retried in a later separately approved window, that later
artifact must explicitly version a new idempotency key rather than improvising
one.

## 6. Exact invocation command

The exact invocation command to be reviewed in a future authorized window is:

```bash
curl -sS \
  -X POST http://127.0.0.1:8000/trade-gate/testnet-order-intents \
  -H 'Content-Type: application/json' \
  --data '{"symbol":"BTCUSDT","side":"BUY","notional":4,"stop_price":68000,"order_type":"market","created_by":"baolood","idempotency_key":"testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1"}'
```

This packet fixes that command as the future execution candidate.

This document still does **not** authorize actually running it.

## 7. Exact success-evidence capture commands

If a future authorized window executes the invocation command and returns
`status = ok`, the exact evidence capture set should be:

1. capture raw invocation response
2. capture resulting `command_id`
3. fetch command detail for that `command_id`
4. capture stage health and worker status

Approved success-evidence command set:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/ops/state
curl -sS http://127.0.0.1:8000/ops/worker
curl -sS http://127.0.0.1:8000/domain-commands/<command_id>
```

The response body from the POST and the later `domain-commands/<command_id>`
fetch together form the minimum success evidence chain.

## 8. Exact blocked-evidence capture commands

If a future authorized window runs the invocation command and receives:

```text
status = error
```

then the exact blocked-evidence set should be:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/ops/state
curl -sS http://127.0.0.1:8000/ops/worker
```

Blocked evidence must preserve:

- raw invocation response
- normalized rejection reason
- current health surface
- current worker surface

If no `command_id` is returned, no synthetic command detail should be invented.

## 9. Exact retreat / stop sequence

If the future authorized window becomes uncertain at any point before the POST,
the retreat action is:

```text
DO NOT EXECUTE THE POST
```

If the POST returns `status = error`, the stop sequence is:

1. record raw response
2. record health / ops evidence
3. do not retry inside the same ad hoc step
4. close the window as `BLOCKED` or `FAIL`

If the POST returns `status = ok`, this packet still does not authorize:

- automatic retry
- canary
- go-live
- live trading

The stop sequence after acceptance is:

1. record `command_id`
2. capture evidence
3. stop and review

There is no approval here for chained follow-up execution.

## 10. What is now resolved

This packet resolves the blocker:

```text
NO_SINGLE_APPROVED_OPERATOR_INVOCATION_PACKET
```

because the repo now has one exact invocation shape rather than only a general
endpoint family.

## 11. What is still not resolved

Even with this packet prepared, the following remain unresolved:

- operator window is not reopened yet
- pre-execution check for this exact packet is not run yet
- real external request is not authorized yet
- real external request has not been sent
- canary is not authorized
- go-live is not authorized
- live trading is not authorized

So this packet closes the final packet-definition gap, but not the execution
authorization gap.

## 12. Stable result statement

The correct result statement after this packet is:

```text
exact invocation packet: PREPARED
final execution command approval: still NO
real external request authorization: still NO
real external request sent: NO
go-live: NO-GO
live trading: NO-GO
```

## 13. Required next artifact

The next artifact should now be:

```text
Real External Request Window Authorization Reopen Review
```

Only after that review explicitly reopens the operator window should this exact
packet move into pre-execution check.

## 14. Explicit non-claims

- This packet does not approve execution.
- This packet does not reopen the operator window.
- This packet does not authorize a real external request.
- This packet does not send a real external request.
- This packet does not authorize canary.
- This packet does not authorize go-live.
- This packet does not authorize live trading.

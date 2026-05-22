# ORDER testnet executor boundary V1

**Status:** boundary design only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering lead, interim).

**Date:** 2026-05-22

**Scope:** define the future real testnet executor boundary for the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement the boundary. It defines what the boundary must do before real testnet execution is allowed.

## 1. Decision

The future real testnet executor boundary belongs under:

```text
ORDER + execution_mode=testnet
```

It does **not** belong under:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
```

The boundary must be a separate execution step after contract validation, risk checks, and kill switch checks, but before any signed HTTP request.

## 2. Boundary shape

Target flow:

```text
Command persisted
-> worker claims ORDER command
-> validate payload / contract
-> policy checks
-> risk checks
-> kill switch check
-> testnet executor boundary
-> normalize response
-> ACTION_OK / ACTION_FAIL
-> MARK_DONE / MARK_FAILED
```

The boundary begins exactly at:

```text
"we are about to transform a valid ORDER testnet command into an external testnet request"
```

and ends at:

```text
"we have a normalized result or normalized error ready for command persistence"
```

## 3. Inputs to the boundary

The executor boundary should receive a normalized object like:

```text
command_id
attempt
execution_mode=testnet
market
symbol
side
notional
order_type
limit_price?
stop_price
source
created_by
idempotency_key
```

It must not rely on:

- raw UI payload shape
- global `EXECUTION_MODE=BINANCE_TESTNET`
- generic exchange key names

## 4. Canonical env contract

The boundary must read only the canonical env names:

```text
TESTNET_EXCHANGE_API_KEY
TESTNET_EXCHANGE_API_SECRET
TESTNET_EXCHANGE_BASE_URL
TESTNET_EXCHANGE_KEY_ID
```

Legacy names may be supported only through a temporary adapter layer if migration requires it, but the boundary contract itself should be documented in canonical names only.

Precedence if an adapter exists:

```text
TESTNET_EXCHANGE_* first
BINANCE_* second
```

## 5. Preconditions before external request

The boundary must refuse to send any external request unless all of these are true:

```text
type == ORDER
execution_mode == testnet
market is testnet-capable
symbol allowed
idempotency_key present
source allowed
created_by present
stop_price valid
policy checks passed
risk checks passed
kill switch OFF
canonical credentials present
base URL points to testnet
```

If any precondition fails:

```text
no signed HTTP
no external order request
command becomes FAILED with normalized reason
```

## 6. What the boundary is allowed to do

Allowed:

- load canonical testnet credentials
- construct a testnet-only HTTP request
- send signed request to testnet host
- parse exchange response
- normalize success/failure into command result/error

Not allowed:

- call live endpoints
- guess environment from ambiguous hostnames
- bypass risk or kill switch
- mutate command status outside normal runner path
- hide upstream failures behind fake local success

## 7. Expected event evidence

The future real testnet path should emit enough evidence to distinguish:

```text
contract accepted
executor requested
executor authenticated
executor rejected by upstream
network timeout
kill switch blocked
final DONE
final FAILED
```

Recommended target event sequence for success:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_ACCEPTED
ACTION_OK
MARK_DONE
```

Recommended target sequence for upstream/auth/network failure:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_REJECTED
ACTION_FAIL
MARK_FAILED
```

The current local-only `TESTNET_EXECUTOR_STUB` event should remain a stub-only signal and must not be reused as the real-executor success signal.

## 8. Result normalization

The boundary must normalize successful response data into a predictable result shape, for example:

```json
{
  "ok": true,
  "type": "order",
  "execution_mode": "testnet",
  "market": "binance_testnet",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "notional": 4.0,
  "order_type": "market",
  "source": "trade_gate_v1",
  "created_by": "baolood",
  "stop_price": 68000.0,
  "external_order_id": "<exchange order id>",
  "external_status": "<exchange status>",
  "ts": "<iso8601>"
}
```

Errors should normalize into stable failure families, such as:

```text
TESTNET_CONTRACT_REJECTED
TESTNET_CREDENTIALS_MISSING
TESTNET_BASE_URL_INVALID
TESTNET_EXECUTOR_AUTH_FAILED
TESTNET_EXECUTOR_REJECTED
TESTNET_EXECUTOR_TIMEOUT
TESTNET_EXECUTOR_NETWORK_ERROR
KILL_SWITCH_ON
POLICY_BLOCK
RISK_HARD_LIMITS_...
```

## 9. Relationship to the legacy path

The legacy `QUOTE + BINANCE_TESTNET` branch is not the target boundary.

If migration work borrows implementation details from it, those details must be reattached under the new `ORDER` boundary and canonical env names.

Do not let the migration keep these legacy assumptions:

- `cmd_type == QUOTE`
- global `EXECUTION_MODE=BINANCE_TESTNET` as the main selector
- generic `BINANCE_API_KEY` naming

## 10. Minimum implementation staging

Recommended implementation staging:

1. **Boundary adapter stub**
   Keep local behavior, but shape inputs/outputs as the future real boundary.

2. **Credential presence gate**
   Validate canonical env names without sending HTTP.

3. **Signed testnet request path**
   Send request only when all gates are satisfied.

4. **Response normalization**
   Normalize exchange result/error into stable command output.

5. **Real testnet smoke**
   Prove success, auth failure, network failure, and kill switch block.

## 11. What not to do

- Do not wire real testnet execution directly into the current stub branch.
- Do not keep the old `QUOTE` path as the unofficial “real path” while documenting `ORDER` elsewhere.
- Do not let real executor success emit `TESTNET_EXECUTOR_STUB`.
- Do not read generic `BINANCE_*` names as the long-term contract.
- Do not add real keys before a smoke spec exists.
- Do not treat this boundary design as live approval.

## 12. Acceptance for this boundary design

```text
ORDER chosen as canonical executor boundary: PASS
legacy QUOTE path excluded from future boundary: PASS
canonical TESTNET_EXCHANGE_* env names required: PASS
pre-request gates defined: PASS
kill switch placement defined: PASS
success/failure event targets defined: PASS
result/error normalization defined: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

## 13. Next single task

Recommended next task:

```text
Real Testnet Smoke Spec V1
```

Scope:

- docs only
- define PASS/FAIL evidence for future real testnet smoke
- no real key
- no external API call
- no live trading

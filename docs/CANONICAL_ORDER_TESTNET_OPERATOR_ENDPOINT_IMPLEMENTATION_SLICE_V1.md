# Canonical ORDER:testnet Operator Endpoint Implementation Slice V1

## 1. Purpose

This artifact defines the minimum code-writing slice required to implement the
selected canonical operator-facing endpoint for:

```text
ORDER + execution_mode=testnet
```

This slice is still planning-only. It does not write code, does not authorize a
real external request, and does not open a new operator window.

## 2. Current status

- implementation slice prepared: YES
- minimum write scope fixed: YES
- canonical operator endpoint selected already: YES
- canonical operator endpoint implemented now: NO
- final execution command approved now: NO
- real external request authorized now: NO
- real external request sent now: NO
- canary executed now: NO
- go-live: NO-GO
- live trading: NO-GO

## 3. Selected endpoint target

The selected operator-facing target remains:

```text
POST /trade-gate/testnet-order-intents
```

This endpoint should create canonical `ORDER:testnet` commands and return a
reviewable `command_id`, while preserving runtime-owned execution and evidence.

## 4. Minimum write scope

The minimum intended write scope is:

### Backend route and helpers

- `anchor-backend/app/main.py`

Expected changes:

- add `POST /trade-gate/testnet-order-intents`
- add `_validate_trade_gate_testnet_order_request(...)`
- add `_build_trade_gate_testnet_order_payload(...)`

### Console proxy

- `anchor-console/app/api/trade-gate/testnet-order-intents/route.ts`

Expected changes:

- add a new proxy route matching the backend endpoint
- preserve existing `dry-run-intents` route unchanged

### Backend contract test

- `anchor-backend/tests/test_trade_gate_testnet_order_intent_v1.py`

Expected changes:

- add dedicated contract tests for the new endpoint
- prove payload creation uses canonical `ORDER:testnet` fields
- prove the route does not silently downgrade to `dry_run`

### Checklist evidence

- `docs/GO_LIVE_CHECKLIST.md`

Expected changes:

- record implementation slice prepared
- keep endpoint unimplemented until code actually lands

## 5. Explicitly out of scope

This slice must not:

- modify `anchor-backend/app/actions/runner.py`
- modify `anchor-backend/app/executors/testnet_order_executor.py`
- modify worker execution semantics
- open a real external request window
- send a real external request
- authorize canary execution
- authorize go-live
- authorize live trading

It also must not silently repurpose:

- `POST /trade-gate/dry-run-intents`
- `POST /domain-commands/quote`
- direct shell scripts
- generic `POST /commands`

## 6. Expected backend contract

The new backend route should validate and construct a payload containing at
least:

- `type = ORDER`
- `execution_mode = testnet`
- `market = binance_testnet`
- `source = ops_manual`
- `created_by = operator identity`
- `symbol`
- `side`
- `notional`
- `stop_price`
- `order_type`
- `idempotency_key`

The route should not inline-send the external request. It should only create
the canonical command and return `command_id`.

## 7. Expected test assertions

The dedicated test file should prove at minimum:

1. valid request creates an `ORDER` command
2. payload uses `execution_mode = testnet`
3. payload uses `source = ops_manual`
4. payload includes `created_by`
5. payload requires `stop_price`
6. route does not accept `live` execution mode
7. route does not produce `dry_run`
8. route returns `status = ok` and `command_id` on acceptance
9. route returns normalized `status = error` on contract rejection

## 8. Expected code-review guardrails

The implementation slice should be rejected if it:

- edits more than the minimum route/proxy/test files without strong reason
- changes existing dry-run contract behavior
- changes worker or executor behavior
- adds automatic retry
- adds live-trading capability
- introduces direct shell execution as the operator path

## 9. Required next artifact

After this slice is accepted, the next artifact should be one of:

```text
Canonical ORDER:testnet Operator Endpoint Implementation
```

or, if code is written in the next round:

```text
Canonical ORDER:testnet Operator Endpoint Implementation Closeout
```

Only after implementation exists should the final execution packet be revisited.

## 10. Explicit non-claims

- This slice does not implement the endpoint.
- This slice does not approve a final execution command.
- This slice does not authorize a real external request.
- This slice does not send a real external request.
- This slice does not authorize canary execution.
- This slice does not authorize go-live.
- This slice does not authorize live trading.

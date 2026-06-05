# Canonical ORDER:testnet Operator Endpoint Decision And Implementation Plan V1

## 1. Purpose

This artifact resolves the blocker identified by the final single-command
execution packet:

```text
NO_CANONICAL_OPERATOR_ENDPOINT_FOR_ORDER_TESTNET
```

It does not implement code. It decides which operator-facing endpoint should
exist for the canonical future bounded real external request path and fixes the
minimum implementation plan needed to create it.

## 2. Current status

- operator endpoint decision prepared: YES
- canonical operator endpoint selected: YES
- canonical operator endpoint implemented now: NO
- final execution command approved now: NO
- real external request authorized now: NO
- real external request sent now: NO
- canary executed now: NO
- go-live: NO-GO
- live trading: NO-GO

## 3. Problem being solved

The repo already narrowed the future real external request path to:

```text
canonical ORDER + execution_mode=testnet runtime-owned path
```

But the currently visible operator-facing intake is still:

```text
POST /trade-gate/dry-run-intents
```

and that route is explicitly dry-run-only:

- `gate_decision = SIMULATE_ONLY`
- `execution_mode = dry_run`

So the project still lacks one operator-facing repo-tracked intake that creates
canonical `ORDER:testnet` commands.

## 4. Decision

The canonical operator-facing endpoint for the first bounded real external
request path should be a **new dedicated route**, not a reuse of an existing
dry-run or generic route.

Selected backend endpoint:

```text
POST /trade-gate/testnet-order-intents
```

Selected console proxy:

```text
anchor-console/app/api/trade-gate/testnet-order-intents/route.ts
```

Selected command identity:

```text
Command.type = ORDER
payload.execution_mode = testnet
payload.source = ops_manual
```

## 5. Why this route was selected

This route is selected because it best preserves all three truths already fixed
in the repo:

1. the canonical future path is `ORDER + execution_mode=testnet`
2. the first bounded real external request must remain runtime-owned and
   evidence-rich
3. the existing `/trade-gate/dry-run-intents` contract must not be silently
   mutated into a real-request route

This choice keeps the path explicit rather than overloading a dry-run route
with mixed semantics.

## 6. Explicitly rejected options

### Rejected option A. Reuse `POST /trade-gate/dry-run-intents`

Rejected because current backend code and tests enforce:

- `gate_decision = SIMULATE_ONLY`
- `execution_mode = dry_run`
- dry-run-only contract language

Changing that route in place would blur dry-run and real-request semantics and
would weaken audit clarity.

### Rejected option B. Use generic `POST /commands` as the operator entry

Rejected because it is too generic for the first bounded real external request.

It lacks a path-specific contract that clearly fixes:

- `ORDER:testnet`
- bounded operator intent
- operator-facing payload validation
- path-specific review language

### Rejected option C. Use direct shell scripts

Rejected because direct shell scripts:

- bypass runtime-owned evidence
- bypass canonical command creation
- bypass worker-reviewed domain event flow
- encourage secret handling outside the canonical path

## 7. Fixed implementation shape

The implementation plan should create exactly this shape:

### Backend

Add a new backend intake route in:

```text
anchor-backend/app/main.py
```

with:

- route: `POST /trade-gate/testnet-order-intents`
- dedicated validator:
  - `_validate_trade_gate_testnet_order_request(...)`
- dedicated payload builder:
  - `_build_trade_gate_testnet_order_payload(...)`

### Console

Add a matching proxy route in:

```text
anchor-console/app/api/trade-gate/testnet-order-intents/route.ts
```

### Tests

Add a dedicated intake test file, for example:

```text
anchor-backend/tests/test_trade_gate_testnet_order_intent_v1.py
```

The implementation should keep existing dry-run tests intact and add a separate
contract for the canonical testnet operator path.

## 8. Fixed payload expectations

The future route must create a command payload that includes at least:

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

It must not silently downgrade to:

- `execution_mode = dry_run`
- `source = trade_gate_v1`
- `gate_decision = SIMULATE_ONLY`

## 9. Fixed response expectations

The future route should return a minimal response of the form:

### Success

```json
{
  "status": "ok",
  "command_id": "<id>"
}
```

### Contract rejection

```json
{
  "status": "error",
  "error": "<normalized reason>"
}
```

The route should create the canonical command, not perform the real request
inline.

## 10. Boundary rules

Even after the endpoint exists, all of these remain true until a later window:

- final execution command approved now: NO
- real external request authorized now: NO
- real external request sent now: NO
- canary executed now: NO
- go-live: NO-GO
- live trading: NO-GO

This decision only selects the missing operator-facing intake.

## 11. Required next artifact

The next required artifact is:

```text
Canonical ORDER:testnet Operator Endpoint Implementation Slice
```

That artifact should either:

1. implement the new endpoint and tests, or
2. define the exact code-writing slice if implementation is deliberately
   deferred

Only after that exists should the final execution packet be revisited.

## 12. Explicit non-claims

- This decision does not implement the new endpoint.
- This decision does not approve a final execution command.
- This decision does not authorize a real external request.
- This decision does not send a real external request.
- This decision does not authorize canary execution.
- This decision does not authorize go-live.
- This decision does not authorize live trading.

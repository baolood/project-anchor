# Simulator Contract Plan V1

## Purpose

Define the mock/exchange-simulator upstream contract before implementation.

The simulator exists to validate upstream contract semantics without external exchange, region, network, or credential dependency. This plan does not implement the simulator, send any request, retry Binance testnet, execute canary, authorize live trading, or mark go-live as GO.

## Contract Scope

- exactly-one request handling
- fixed idempotency key support
- no live trading path
- no real exchange credentials
- deterministic responses
- closeout evidence required after first simulator run
- auditable event chain for accepted, rejected, failed, and duplicate-idempotency cases

## Request Contract

The simulator request contract should align with existing order-intent payload patterns:

- `market`
- `symbol`
- `side`
- `notional`
- `idempotency_key`
- `source`
- `created_by`
- `execution_mode`
- optional `scenario` selector for `ACCEPTED`, `REJECTED`, or `FAILED`, if consistent with existing command payload validation patterns

The request must not include real exchange credentials or live-trading authorization.

## Response Contract

### ACCEPTED

- status: `DONE` according to existing domain result semantics, or `ACCEPTED` if represented as an upstream outcome inside the result payload
- `simulator_order_id` or external_order_id equivalent: present
- `upstream_request_started`: true
- failure fields: absent
- terminal lifecycle event: `MARK_DONE`

### REJECTED

- status: `FAILED` according to existing domain result semantics, with rejected outcome recorded in the result payload
- `simulator_order_id` or external_order_id equivalent: absent
- `upstream_request_started`: true
- rejection reason: present
- terminal lifecycle event: `MARK_FAILED`

### FAILED

- status: `FAILED`
- `simulator_order_id` or external_order_id equivalent: absent
- `upstream_request_started`: true or false depending on the simulated failure phase
- `failure_family`: present
- terminal lifecycle event: `MARK_FAILED`

## Required Event Chain

Every simulator run must include a REQUESTED event before any terminal accepted, rejected, or failed outcome.

Required event evidence:

- REQUESTED event before terminal outcome
- ACCEPTED event for accepted path
- REJECTED event for rejected path
- FAILED event for failed path
- MARK_DONE for accepted command lifecycle
- MARK_FAILED for rejected and failed command lifecycle
- deterministic negative evidence when no external_order_id equivalent should exist

## Idempotency

- fixed idempotency key must be honored
- duplicate request with the same key must not create a second simulator_order_id
- duplicate behavior must be auditable
- duplicate behavior must preserve the original simulator_order_id for accepted path
- duplicate behavior must preserve terminal outcome evidence for rejected and failed paths

## Fixture Matrix

Future implementation must include fixtures for:

- accepted fixture
- rejected fixture
- failed fixture
- duplicate idempotency fixture
- missing/invalid field fixture
- no live-trading fixture

## Implementation Boundary For Future Task

- no implementation in this plan
- future implementation must be minimal
- no new external exchange adapter
- no runtime/env/secrets change unless separately authorized
- no canary
- no live trading
- go-live remains NO-GO
- first simulator run requires a separate exactly-one simulator send task and closeout document

## Next Safe Status

- `SIMULATOR_CONTRACT_PLANNED`
- `READY_FOR_MINIMAL_SIMULATOR_IMPLEMENTATION_PLAN`

## Final State

- simulator contract planned: YES
- simulator implemented: NO
- adapter implemented: NO
- POST sent: NO
- real external request sent: NO
- retry: NO
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

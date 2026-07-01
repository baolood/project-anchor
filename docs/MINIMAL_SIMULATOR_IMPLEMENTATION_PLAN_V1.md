# Minimal Simulator Implementation Plan V1

## Purpose

Plan the smallest safe implementation needed to validate the mock/exchange-simulator contract defined in `docs/SIMULATOR_CONTRACT_PLAN_V1.md`.

This plan does not implement the simulator, send requests, change runtime/env/secrets, execute canary, authorize live trading, or mark go-live as GO.

## Allowed Future Implementation Scope

Future implementation should be limited to:

- one simulator module/helper only
- one integration point into the existing testnet executor path
- fixture/test coverage for ACCEPTED, REJECTED, FAILED, duplicate idempotency, and invalid input
- closeout evidence after the first simulator run

The future implementation must remain minimal and must not introduce a broad exchange adapter abstraction.

## Proposed File Boundaries For Future Implementation

Candidate implementation files:

- `anchor-backend/app/executors/testnet_order_executor.py`
- `anchor-backend/app/executors/simulator_order_executor.py`
- `anchor-backend/app/workers/domain_command_worker.py`
- focused tests under `anchor-backend/tests/` if an existing test structure is present
- a focused checklist script under `scripts/` only if needed to validate the fixture matrix
- a closeout doc under `docs/` after the first simulator run

Forbidden unless separately authorized:

- frontend files
- runtime/env/secrets files
- deploy files
- risk policy files
- database migrations
- production/live trading configuration
- broad new exchange adapter abstraction
- unrelated backend or worker refactors

Migrations should be avoided unless explicitly justified by a future implementation review. Runtime/env/secrets changes are not part of this plan.

## Minimal Simulator Behavior

### ACCEPTED

- returns `simulator_order_id` or external_order_id equivalent
- sets `upstream_request_started` to true
- records accepted outcome evidence
- reaches `MARK_DONE` according to the existing command lifecycle

### REJECTED

- returns no `simulator_order_id`
- returns no external_order_id equivalent
- sets `upstream_request_started` to true
- records rejection reason
- reaches `MARK_FAILED` according to the existing command lifecycle

### FAILED

- returns no `simulator_order_id`
- returns no external_order_id equivalent
- records `failure_family`
- sets `upstream_request_started` according to the simulated failure phase
- reaches `MARK_FAILED` according to the existing command lifecycle

### Duplicate Idempotency

- duplicate idempotency key must not create a second simulator_order_id
- duplicate behavior must be auditable
- duplicate accepted outcome must preserve the original simulator_order_id equivalent
- duplicate rejected or failed outcome must preserve terminal outcome evidence

### Invalid Input

- invalid input must fail before accepted outcome
- invalid input must not create simulator_order_id or external_order_id equivalent
- invalid input must produce deterministic negative evidence

### Live Trading Boundary

- no live trading path
- no real exchange credentials
- no external exchange request

## Event Evidence Requirements

Future implementation must produce auditable evidence:

- REQUESTED before terminal outcome
- ACCEPTED / REJECTED / FAILED according to scenario
- MARK_DONE or MARK_FAILED according to existing command lifecycle
- deterministic negative evidence when external_order_id equivalent is absent
- idempotency evidence for duplicate request handling

## Testing Plan

Future implementation should include:

- unit tests for simulator helper
- command lifecycle tests if the existing structure supports them
- fixture matrix test for accepted, rejected, failed, duplicate idempotency, invalid input, and no live-trading behavior

Required baseline checks after future implementation:

- `bash scripts/check_hardened_order_testnet_one_shot_invocation.sh`
- `bash scripts/check_go_live_rules.sh`
- `bash scripts/check_local_box_baseline.sh`

## Rollback Plan

If future implementation is incorrect:

- revert the implementation commit/PR
- keep simulator path disabled by default if implementation introduces a toggle
- preserve no runtime credential impact
- preserve no live/canary impact
- preserve go-live as NO-GO

## Next Safe Status

- `MINIMAL_SIMULATOR_IMPLEMENTATION_PLANNED`
- `READY_FOR_MINIMAL_SIMULATOR_IMPLEMENTATION`

## Final State

- minimal simulator implementation planned: YES
- simulator implemented: NO
- adapter implemented: NO
- POST sent: NO
- real external request sent: NO
- runtime/env/secrets changed: NO
- retry: NO
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

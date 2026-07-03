# Alternative Adapter Contract Review V1

## Scope

This document reviews the merged minimal alternative testnet adapter skeleton and decides the next safe implementation slice.

This is a contract review only. It does not add an HTTP client, credentials, runtime integration, runner wiring, worker behavior, risk changes, database mutation, canary retry, external request, live trading, or go-live authorization.

## Current Main State

- reviewed main HEAD: `4e0dc0abecef0a973cdf6b3dcfa4b191aadbc960`
- minimal alternative adapter skeleton merged: YES
- adapter module present: `anchor-backend/app/actions/alternative_testnet_executor.py`
- adapter tests present: `tests/test_alternative_testnet_executor.py`
- runtime behavior changed by this review: NO
- credentials changed by this review: NO
- external request sent by this review: NO
- canary retried by this review: NO
- live trading: NO-GO
- go-live: NO-GO

## Skeleton Presence Review

- `anchor-backend/app/actions/alternative_testnet_executor.py` present: YES
- `tests/test_alternative_testnet_executor.py` present: YES
- accepted stub covered: YES
- rejected stub covered: YES
- failed stub covered: YES
- HTTP / network client present: NO
- credential loading present: NO
- environment variable loading present: NO
- runtime path enabled: NO
- runner integration present: NO
- worker integration present: NO
- risk integration present: NO

## Request Contract Review

The request shape is stable enough for the next test-only slice because it carries the minimum evidence required to connect a future adapter decision to a command-level audit trail without enabling runtime use.

Reviewed request fields:

- `command_id`: present, evidence-bearing, stable
- `idempotency_key`: present, used for deterministic evidence
- `venue`: present, identifies the approved alternative testnet boundary
- `symbol`: present, future order-intent evidence field
- `side`: present, future order-intent evidence field
- `notional`: present, future order-intent evidence field
- `scenario`: present, limited to `ACCEPTED`, `REJECTED`, `FAILED`
- `execution_mode`: present, defaults to `testnet`

Contract finding: PASS. The request shape is narrow and does not require credentials, env, network, runner registration, or worker registration.

## Result Contract Review

The result shape is stable enough for the next test-only slice because it preserves explicit terminal evidence without inventing external exchange evidence for rejected or failed paths.

Reviewed result fields:

- `command_id`: present
- `idempotency_key`: present
- `execution_mode`: present
- `venue`: present
- `status`: explicit `ACCEPTED`, `REJECTED`, or `FAILED`
- `failure_family`: explicit on non-accepted paths
- `failure_reason`: explicit on non-accepted paths
- `external_order_id`: present only when accepted stub returns deterministic external-order equivalent
- `external_order_id_present`: explicit boolean evidence

Contract finding: PASS. The result shape is auditable, explicit, and compatible with future command closeout evidence.

## Evidence Semantics Review

- `ACCEPTED` may carry an `external_order_id` equivalent only in deterministic stub form: YES
- `REJECTED` must not invent `external_order_id`: YES
- `FAILED` must not invent `external_order_id`: YES
- `failure_family` must stay explicit on non-accepted paths: YES
- `failure_reason` must stay explicit on non-accepted paths: YES
- idempotency evidence must remain deterministic: YES
- no retry behavior exists in skeleton: YES
- no external request behavior exists in skeleton: YES

Evidence finding: PASS. The contract preserves negative evidence for rejected and failed paths and avoids optimistic external-order assumptions.

## Boundary Review

- code modified in this review: NO
- tests modified in this review: NO
- HTTP / network client added: NO
- credentials added or modified: NO
- env/config/deploy/docker/compose/migrations modified: NO
- runner modified: NO
- worker modified: NO
- risk modified: NO
- runtime registration modified: NO
- database rows modified: NO
- external request sent: NO
- canary retried: NO
- live trading enabled: NO
- go-live enabled: NO

Boundary finding: PASS.

## Next Safe Slice Decision

Recommended next path: `READY_FOR_ADAPTER_CONTRACT_TEST_EXPANSION`.

The next slice should expand contract tests around the existing skeleton without enabling network, credentials, env loading, runtime registration, runner integration, or worker integration.

Explicitly not authorized as the next slice:

- HTTP client: NOT AUTHORIZED
- credentials: NOT AUTHORIZED
- runner integration: NOT AUTHORIZED
- worker integration: NOT AUTHORIZED
- runtime route enablement: NOT AUTHORIZED
- external request: NOT AUTHORIZED
- canary retry: NOT AUTHORIZED
- live trading: NO-GO
- go-live: NO-GO

## Final Verdict

PASS. The minimal alternative testnet adapter skeleton contract is coherent enough to support a future contract test expansion slice. It is not yet an executable external adapter and must remain disconnected from runtime execution until later explicit authorization.

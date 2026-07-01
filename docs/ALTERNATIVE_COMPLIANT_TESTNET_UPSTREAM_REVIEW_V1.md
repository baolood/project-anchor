# Alternative Compliant Testnet Upstream Review V1

## Purpose

Identify the next compliant testnet upstream path after the current local Binance testnet upstream returned HTTP 451 restricted location.

This review is decision preparation only. It does not implement a new adapter, change runtime, change env/secrets, send any request, retry Binance testnet, execute canary, authorize live trading, or mark go-live as GO.

## Current Facts

- exactly-one bounded real testnet send occurred: YES
- upstream external exchange request started: YES
- Binance testnet returned HTTP 451 restricted location: YES
- current local Binance testnet upstream: UNAVAILABLE
- upstream access decision evidence: `docs/TESTNET_UPSTREAM_ACCESS_DECISION_V1.md`
- restricted-location review evidence: `docs/TESTNET_UPSTREAM_RESTRICTED_LOCATION_REVIEW_V1.md`
- command_id: `order-cdf35b49-bc0a-4999-af9b-4e54fb333a61`
- external_order_id_present: false
- retry from same environment: NO
- VPN/geofence bypass: NO
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

## Candidate Paths

### 1. Alternative Compliant Exchange Testnet Upstream

Use a different exchange testnet or sandbox endpoint that is available from the current operating environment and can be used without bypassing access controls.

Review focus:

- official sandbox/testnet availability
- terms-compatible access from the current environment
- order-intent compatibility with Project Anchor's `ORDER:testnet` path
- ability to produce an external order id or equivalent test execution id
- ability to test accepted, rejected, and failed outcomes
- credential isolation from production credentials
- no live trading route enabled by default
- minimal adapter/config surface

### 2. Mock Or Exchange-Simulator Upstream With Production-Like Contract

Use a local or controlled simulator that implements a production-like exchange contract while keeping all requests offline or inside a bounded non-live environment.

Review focus:

- deterministic accepted, rejected, and failed outcomes
- production-like response shape, including external_order_id or equivalent simulated id
- no real external exchange request
- no live trading route
- strong auditability and repeatability
- minimal risk while validating downstream state transitions

### 3. Separately Authorized Compliant Allowed-Region Execution Environment

Use a compliant execution environment from an allowed region only if separately approved.

This option is listed for completeness but is not authorized by this review. It would require a separate environment, secrets, deployment, network, compliance, and operational risk review before any implementation or execution.

## Decision Criteria

Any upstream candidate must be evaluated against:

- compliance and availability from the intended execution environment
- API compatibility with Project Anchor's order-intent contract
- ability to return `external_order_id` or an equivalent stable execution identifier
- ability to test ACCEPTED, REJECTED, and FAILED outcomes
- credential isolation from production and other environments
- no live trading path enabled by default
- minimal code changes
- rollback and auditability
- compatibility with existing guardrails, kill switch checks, idempotency, and closeout evidence

## Recommended Next Path

Prefer alternative compliant testnet upstream review and selection first.

Do not introduce an allowed-region remote executor yet unless explicitly approved in a separate task. Do not bypass geofence controls. Do not retry Binance testnet from the current restricted local environment.

The next task should select one upstream candidate or decide that a mock/exchange-simulator path is the safest intermediate step before another real testnet upstream.

## Next Safe Status

- `ALTERNATIVE_COMPLIANT_TESTNET_UPSTREAM_REVIEWED`
- `WAITING_FOR_UPSTREAM_SELECTION`

## Boundary

- POST sent: NO
- retry: NO
- real external exchange request sent: NO
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO
- runtime/env/secrets changed: NO
- backend/worker/risk/deploy changed: NO
- new exchange adapter implemented: NO
- VPN/geofence bypass recommended: NO

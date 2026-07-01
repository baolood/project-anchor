# Testnet Upstream Selection Decision V1

## Scope

Select the next compliant upstream path after the alternative compliant testnet upstream review.

This decision is not an implementation. It does not send requests, retry Binance testnet, implement a simulator, implement a new exchange adapter, change runtime/env/secrets, execute canary, authorize live trading, or mark go-live as GO.

## Decision

- selected path: mock/exchange-simulator upstream
- reason: lowest-risk compliant path to validate upstream contract semantics
- decision type: upstream selection decision, not implementation
- selected external exchange testnet now: NO
- selected allowed-region remote executor now: NO
- Binance retry selected: NO
- VPN/geofence bypass selected: NO

## Preserved Facts

- current local Binance testnet upstream: UNAVAILABLE
- reason: HTTP 451 restricted location
- upstream access decision evidence: `docs/TESTNET_UPSTREAM_ACCESS_DECISION_V1.md`
- alternative upstream review evidence: `docs/ALTERNATIVE_COMPLIANT_TESTNET_UPSTREAM_REVIEW_V1.md`
- retry from same environment: NO
- VPN/geofence bypass: NO
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

## Why Simulator First

The mock/exchange-simulator path is selected first because it:

- validates REQUESTED / ACCEPTED / REJECTED / FAILED outcomes
- can produce an `external_order_id` equivalent for accepted paths
- supports deterministic negative evidence
- avoids new exchange credentials
- avoids new region and network dependencies
- keeps rollback simple
- preserves auditability
- keeps all requests away from live trading paths
- allows the upstream contract to be verified before another external upstream is selected

## Future Simulator Contract Requirements

Future implementation must be separately authorized and must define:

- exactly-one request handling
- fixed idempotency key enforcement
- deterministic `external_order_id` generation for accepted path
- accepted outcome
- rejected outcome
- failed outcome
- no live trading path
- no real exchange credentials
- clear event chain evidence
- closeout document required after first simulator run

## Not Selected Now

- alternative external exchange testnet
- allowed-region remote executor
- Binance retry
- VPN/geofence bypass

## Next Safe Status

- `SELECTED_MOCK_EXCHANGE_SIMULATOR`
- `READY_FOR_SIMULATOR_CONTRACT_PLAN`

## Final State

- selected upstream path: mock/exchange-simulator
- simulator implemented: NO
- POST sent: NO
- retry: NO
- real external exchange request sent: NO
- canary: NOT EXECUTED
- live trading: NO-GO
- go-live: NO-GO

# Approved Alternative Testnet Canary Prep V1

## 1. Purpose

Prepare a future canary path using an approved alternative official testnet, sandbox, demo, or paper-trading venue after Binance testnet returned `FAILED/http_451`.

This prep is documentation only:

- canary retried in this task: NO
- external request sent in this task: NO
- simulator replay executed in this task: NO
- DB mutation performed in this task: NO
- executor / network / location / proxy / VPN changed: NO
- credentials added or changed: NO
- runtime behavior changed: NO
- backend / worker / risk / deploy changed: NO

## 2. Current State

- alternative testnet venue review merged: YES
- source review: `docs/ALTERNATIVE_TESTNET_VENUE_REVIEW_V1.md`
- recommended next path: `READY_FOR_APPROVED_ALTERNATIVE_TESTNET_CANARY_PREP`
- Binance canary result remains FAILED/http_451: YES
- Binance same-path retry rejected: YES
- ad hoc VPN/proxy workaround rejected: YES
- live trading: NO-GO
- go-live: NO-GO

## 3. Approved Alternative Venue Prep Boundary

This artifact only prepares the future boundary. It does not execute or configure the future path.

- prep only: YES
- credentials added: NO
- credentials modified: NO
- API integration changed: NO
- external request sent: NO
- canary authorized: NO
- runtime behavior changed: NO
- executor / network / location / proxy / VPN changed: NO
- go-live authorized: NO
- live trading authorized: NO

## 4. Future Venue Requirements

A future alternative venue canary path must document and satisfy all of the following before any execution can be considered:

- official testnet, sandbox, demo, or paper-trading venue
- no real-money exposure
- documented API order endpoint
- region/access path known before execution
- credential model documented before use
- supports bounded market/limit test order equivalent
- can preserve exactly-one request evidence
- can preserve DONE / FAILED event chain evidence
- can preserve idempotency key or client-order-id evidence
- can map into `commands_domain -> domain_command_worker -> DONE / FAILED`

## 5. Future Implementation Boundary

Future work remains separated into explicitly authorized steps:

1. Separate implementation plan required before any code change.
2. Separate credentials setup authorization required before adding or modifying any credentials.
3. Separate runtime / executor change authorization required before any runtime behavior changes.
4. Separate canary authorization required before any canary execution.
5. No retry if evidence is incomplete.
6. No second canary without new authorization.
7. No go-live escalation.
8. No live trading escalation.

This prep does not authorize implementation, credentials, runtime changes, canary execution, go-live, or live trading.

## 6. Expected Future Evidence

A future alternative venue canary closeout must record:

- venue name
- sandbox/testnet URL or documented access path
- credential presence check by name only, not credential values
- command_id
- idempotency key or client-order-id equivalent
- request timestamp
- execution mode
- event chain
- final status
- external_order_id presence/absence based on actual result
- duplicate request sent: NO
- retry sent: NO
- second canary request sent: NO
- real-money exposure: NO
- live trading: NO-GO
- go-live: NO-GO

## 7. Stop Conditions For Future Prep

A future alternative venue canary prep must stop if any of the following cannot be documented:

- official non-real-money testnet/sandbox/demo/paper-trading status
- credential boundary without exposing secret values
- region/access compatibility without ad hoc VPN/proxy workaround
- endpoint family and expected request shape
- idempotency/client-order-id mapping
- exact evidence requirements
- rollback/stop rule for incomplete evidence
- live trading and go-live NO-GO boundary

## 8. Boundary Preserved

- canary retried: NO
- external request sent in this task: NO
- DB mutation performed in this task: NO
- simulator replay executed: NO
- executor / network / location / proxy / VPN changed: NO
- backend / worker / risk / deploy changed: NO
- runtime / env / secrets changed: NO
- credentials changed: NO
- live trading: NO-GO
- go-live: NO-GO

## 9. Next Safe Status

- `READY_FOR_APPROVED_ALTERNATIVE_TESTNET_CANARY_PREP_PR_MERGE`

After this prep is merged and baseline is clean, the next possible status is implementation planning. This prep does not authorize canary retry, external requests, credentials, runtime changes, go-live, or live trading.

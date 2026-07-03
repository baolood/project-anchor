# Adapter Implementation Gap Review V1

## Scope

This document reviews the current alternative testnet adapter skeleton plus expanded contract tests and identifies the next minimal safe implementation slice.

This is a review-only task. It does not modify adapter code, tests, credentials, env/config, deploy, docker, compose, migrations, runner, worker, risk, runtime registration, database rows, canary behavior, external request behavior, live trading, or go-live state.

## Current State Confirmation

- reviewed main HEAD: `5ffe9a3d4846b7fa88c7c6571ceb0da7bde712c5`
- minimal alternative adapter skeleton merged: YES
- adapter contract review merged: YES
- adapter contract test expansion merged: YES
- adapter tests: PASS, 11 tests
- simulator tests: PASS, 5 tests
- runtime behavior changed: NO
- credentials changed: NO
- external request sent: NO
- canary retried: NO
- live trading: NO-GO
- go-live: NO-GO

## Current Implementation Surface

Current approved alternative testnet surface is intentionally local-only and deterministic:

- request/result dataclass contract: present
- deterministic `ACCEPTED` stub: present
- deterministic `REJECTED` stub: present
- deterministic `FAILED` stub: present
- external-order equivalent only on accepted stub: present
- explicit failure family/reason on rejected and failed stubs: present
- expanded local contract tests: present
- runtime registration: absent
- network behavior: absent
- credential behavior: absent

## Identified Gaps

The following gaps are real and expected. They are not blockers for the current skeleton, but they define what remains before any future alternative venue canary can be considered.

- real venue adapter implementation: NOT PRESENT
- HTTP client: NOT PRESENT
- credential loading: NOT PRESENT
- env/config path: NOT PRESENT
- runner integration: NOT PRESENT
- worker integration: NOT PRESENT
- risk integration: NOT PRESENT
- runtime registration: NOT PRESENT
- external request capability: NOT PRESENT
- alternative venue canary path: NOT PRESENT
- command-domain event mapping for alternative venue: NOT PRESENT
- runtime preflight for alternative venue: NOT PRESENT

## Unsafe Next Steps Rejected

The next slice must not jump to high-risk external integration. These steps remain explicitly rejected for the next slice:

- HTTP client: REJECTED FOR NEXT SLICE
- credential setup: REJECTED FOR NEXT SLICE
- env/config loading: REJECTED FOR NEXT SLICE
- runner integration: REJECTED FOR NEXT SLICE
- worker integration: REJECTED FOR NEXT SLICE
- risk integration: REJECTED FOR NEXT SLICE
- runtime registration: REJECTED FOR NEXT SLICE
- external request: REJECTED FOR NEXT SLICE
- canary authorization: REJECTED FOR NEXT SLICE
- go-live: NO-GO
- live trading: NO-GO

## Recommended Next Safe Slice

Recommended next path: `READY_FOR_ADAPTER_REQUEST_VALIDATION_SLICE`.

Reason: request validation is safer than HTTP/client integration because it can be implemented and tested entirely locally. It strengthens the adapter boundary before any future network, credentials, runtime, or command-domain integration exists.

## Next Slice Boundary

The next implementation slice should be limited to local request validation only:

- add or strengthen local request validation: YES
- keep deterministic local behavior: YES
- add unit tests for invalid local request fields: YES
- no network call: YES
- no HTTP client: YES
- no credentials: YES
- no env loading: YES
- no runtime registration: YES
- no runner changes: YES
- no worker changes: YES
- no risk changes: YES
- no database changes: YES
- no external request: YES
- no canary retry: YES
- live trading remains NO-GO: YES
- go-live remains NO-GO: YES

## Validation Expectations For Next Slice

Future request validation slice should prove, with local tests only, that invalid input cannot silently become accepted evidence. Suggested validation targets:

- empty `command_id` fails deterministically
- empty `idempotency_key` fails deterministically
- empty `venue` fails deterministically
- `execution_mode` other than `testnet` fails deterministically
- empty `symbol` fails deterministically
- invalid `side` fails deterministically
- non-positive `notional` fails deterministically
- unsupported scenario remains non-accepted
- rejected/failed paths continue not to invent external order ids
- no credentials or network fields appear in result evidence

These targets are recommendations only. They do not authorize implementation in this review task.

## Boundary Confirmation For This Review

- adapter implementation modified in this task: NO
- tests modified in this task: NO
- HTTP / network client added in this task: NO
- credentials added or changed in this task: NO
- env/config/deploy/docker/compose/migrations modified in this task: NO
- runner / worker / risk modified in this task: NO
- runtime path enabled in this task: NO
- database rows modified in this task: NO
- external request sent in this task: NO
- canary retried in this task: NO
- live trading enabled: NO
- go-live enabled: NO

## Final Verdict

PASS. The next minimal safe implementation slice should be `READY_FOR_ADAPTER_REQUEST_VALIDATION_SLICE`. Do not proceed to HTTP client, credentials, runner integration, canary, live trading, or go-live from this review.

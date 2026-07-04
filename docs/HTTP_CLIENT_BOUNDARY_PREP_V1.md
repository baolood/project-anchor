# HTTP Client Boundary Prep V1

## Purpose

Prepare the boundary for a future local-only HTTP client skeleton for the
approved alternative testnet adapter. This document does not implement an HTTP
client, load credentials, read env/config, register runtime paths, execute
canary, or send any external request.

## Current Local Adapter Baseline

- main HEAD before prep: `c426269 Merge pull request #184 from baolood/codex/adapter-mapping-closeout-review`
- minimal alternative adapter skeleton merged: YES
- request validation merged: YES
- response/result mapping merged: YES
- mapping closeout review merged: YES
- adapter tests: PASS, 23 tests
- simulator tests: PASS, 5 tests
- HTTP / network client added: NO
- credentials changed: NO
- env/config read added: NO
- runtime path enabled: NO
- external request sent: NO

## Future HTTP Client Boundary

The next HTTP-related slice must remain skeleton-only unless separately
authorized by the operator.

- real network request in first HTTP client slice: NO
- credential loading in first HTTP client slice: NO
- env/config reading in first HTTP client slice: NO
- runner integration in first HTTP client slice: NO
- worker/risk integration in first HTTP client slice: NO
- runtime registration in first HTTP client slice: NO
- canary execution in first HTTP client slice: NO
- external request in tests: NO

## Future Client Interface Expectations

A future skeleton client may only model local request/response shape.

- accepts already-validated local request object: YES
- returns local response fixture/result object: YES
- preserves idempotency_key: YES
- preserves venue: YES
- preserves execution_mode: YES
- maps accepted/rejected/failed through existing response mapping: YES
- never invents external_order_id: YES
- never introduces retry behavior: YES
- never implies network request was sent: YES

## Forbidden Shortcuts

- production endpoint: FORBIDDEN
- live credentials: FORBIDDEN
- fallback to live: FORBIDDEN
- automatic retry: FORBIDDEN
- proxy/VPN workaround: FORBIDDEN
- external request during tests: FORBIDDEN
- env/config loading: FORBIDDEN
- runner/worker/risk integration: FORBIDDEN
- canary authorization: FORBIDDEN
- go-live or live trading: FORBIDDEN

## Future Validation Requirements

- unit tests only: YES
- mocked/local response only: YES
- no socket/network call: YES
- no credential leakage: YES
- adapter tests PASS: REQUIRED
- simulator tests PASS: REQUIRED
- hardened one-shot guardrail PASS: REQUIRED
- go-live rules PASS: REQUIRED
- local box baseline PASS: REQUIRED
- git diff --check PASS: REQUIRED

## Recommendation

- recommended next path: `READY_FOR_HTTP_CLIENT_SKELETON_AUTHORIZATION`
- next step type: explicit authorization for a skeleton-only code slice
- HTTP client implementation authorized by this prep: NO
- credentials authorized by this prep: NO
- external request authorized by this prep: NO
- canary authorized by this prep: NO
- runtime integration authorized by this prep: NO

## Final State

- HTTP client boundary prep added: YES
- runtime behavior changed: NO
- credentials changed: NO
- external request sent: NO
- live trading: NO-GO
- go-live: NO-GO
- next safe status: `READY_FOR_HTTP_CLIENT_BOUNDARY_PREP_PR_MERGE`

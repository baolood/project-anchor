# Real testnet external executor real wire plan V1

**Status:** implementation plan only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-23

**Scope:** define the exact transition from the current mocked external executor boundary to the first real testnet request for the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not perform the transition. It fixes the smallest safe real-wire plan before any credential-backed network call is allowed.

## 1. Decision

The next non-doc implementation slice after mocked executor V1 should be:

```text
replace mocked external request with one real testnet request path
without changing preflight semantics
without adding retry
without widening path ownership
```

Meaning:

- keep canonical `ORDER + execution_mode=testnet`
- keep current preflight refusal behavior unchanged
- keep current mocked event semantics as the reference shape
- switch only the executor helper from mock response to one real bounded request

Still not allowed:

- live trading
- automatic retry
- multi-venue expansion
- generic exchange abstraction rewrite
- legacy `QUOTE + BINANCE_TESTNET` path promotion

## 2. Preconditions before real wire

The real-wire slice should not begin unless all of these are already true:

- mocked external executor path is green in tests
- preflight refusal families remain stable
- `/commands/[id]` can distinguish preflight vs external-attempt evidence
- canonical env contract is fixed to `TESTNET_EXCHANGE_*`
- host-safety rule is fixed to exact HTTPS origin allowlist
- kill-switch source rule is fixed to merged runtime state
- timeout posture remains `single_attempt_v1`
- replay/idempotency posture remains explicit operator replay only

If any of those are still ambiguous, real-wire should wait.

## 3. Exact write scope

Primary write scope:

- `anchor-backend/app/actions/runner.py`
- `anchor-backend/app/executors/testnet_order_executor.py`
- `anchor-backend/tests/test_testnet_external_executor_v1.py`
- `anchor-backend/tests/test_testnet_real_wire_v1.py`

Optional small helper scope, only if needed for pure normalization:

- `anchor-backend/app/executors/__init__.py`

Out of scope:

- frontend
- `anchor-console`
- deploy files
- docker compose
- risk rules
- live executor
- replay implementation

## 4. Runtime mode transition rule

The current mocked boundary is enabled by:

```text
TESTNET_EXECUTOR_MODE=mock
```

The first real-wire slice should add one explicit real mode, for example:

```text
TESTNET_EXECUTOR_MODE=real
```

Rules:

- unset or unknown mode must not silently go real
- `mock` remains available for offline verification
- `real` is the only mode allowed to initiate credential-backed network calls
- `live` remains invalid

This prevents accidental drift from tests or local shells into real external behavior.

## 5. Canonical runtime prerequisites

Before the real helper sends any request, runtime must already have passed:

- canonical path identity
- contract validation
- policy/risk checks
- merged kill switch check
- host safety check
- canonical credential presence check

Additional real-wire prerequisites:

- `TESTNET_EXECUTOR_MODE=real`
- `TESTNET_EXCHANGE_BASE_URL` matches the canonical allowed origin exactly
- `TESTNET_EXCHANGE_API_KEY` present
- `TESTNET_EXCHANGE_API_SECRET` present
- `TESTNET_EXCHANGE_KEY_ID` present for review-safe identification

If any prerequisite fails:

```text
no signed HTTP
preserve current preflight refusal family
```

## 6. Helper ownership in real mode

The real executor helper should own only:

- request construction
- request signing
- one bounded outbound call
- upstream response parsing
- normalized success/failure shaping

It must not own:

- DB writes
- final status transitions
- policy/risk decisions
- kill switch reads
- automatic replay

Runner remains the boundary owner; helper remains the transport/normalization unit.

## 7. First request posture

The first real request should stay intentionally narrow:

- one order
- one symbol path already exercised in dry-run/testnet docs
- one bounded response window
- one attempt only
- no background polling loop

This slice should prove:

```text
we can cross the real boundary once,
normalize success or failure,
and preserve review evidence
```

It should not try to prove throughput, robustness under churn, or replay behavior.

## 8. Event plan for real wire

The current mocked event family already provides the target shape:

```text
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_ACCEPTED
TESTNET_EXECUTOR_REJECTED
```

Real-wire must preserve that shape.

Additional expectations:

- `REQUESTED` should include review-safe mode label like `executor_mode=real`
- `ACCEPTED` must include `external_order_id`
- `REJECTED` must include normalized `failure_family`
- `TESTNET_EXECUTOR_STUB` must remain absent on real-wire paths

If real-wire changes event names or weakens this evidence, the slice is too large.

## 9. Success path requirements

For the first real accepted request:

- `TESTNET_EXECUTOR_REQUESTED` exists
- `TESTNET_EXECUTOR_ACCEPTED` exists
- `ACTION_OK` exists
- `MARK_DONE` exists
- result contains `external_order_id`
- result contains `external_status`
- result contains `host_label`
- result contains `idempotency_key`

If any of those are missing, the command must not be treated as canonical real-wire success.

## 10. Failure path requirements

For the first real rejected request:

- `TESTNET_EXECUTOR_REQUESTED` exists
- `TESTNET_EXECUTOR_REJECTED` exists
- `ACTION_FAIL` exists
- `MARK_FAILED` exists
- normalized `failure_family` is one of:
  - `TESTNET_EXECUTOR_AUTH_FAILED`
  - `TESTNET_EXECUTOR_VALIDATION_FAILED`
  - `TESTNET_EXECUTOR_REJECTED`
  - `TESTNET_EXECUTOR_TIMEOUT`
  - `TESTNET_EXECUTOR_NETWORK_ERROR`
  - `TESTNET_EXECUTOR_UNEXPECTED`

This must still be distinguishable from preflight refusal.

## 11. Negative evidence rules

### If command was blocked before external request

- no `TESTNET_EXECUTOR_REQUESTED`
- no `TESTNET_EXECUTOR_ACCEPTED`
- no `external_order_id`

### If command attempted external request and failed

- `TESTNET_EXECUTOR_REQUESTED` exists
- `TESTNET_EXECUTOR_REJECTED` exists
- `external_order_id` may be absent
- family must explain failure

### If command attempted external request and succeeded

- `TESTNET_EXECUTOR_REQUESTED` exists
- `TESTNET_EXECUTOR_ACCEPTED` exists
- `external_order_id` exists

These distinctions remain mandatory for `/commands/[id]`.

## 12. Timeout and replay posture

Real-wire must inherit the already-fixed rules:

- one external attempt per command attempt
- timeout => `TESTNET_EXECUTOR_TIMEOUT`
- no automatic retry
- operator replay only in a later bounded slice

The first real-wire slice must not introduce:

- implicit re-send after timeout
- hidden follow-up polling that changes success semantics
- silent second external attempt

## 13. Credential safety posture

Real-wire must preserve:

- credentials come only from runtime env
- no secrets in payload
- no secrets in git-tracked files
- no raw secret values in events or result

Allowed review-safe metadata:

- `TESTNET_EXCHANGE_KEY_ID`
- key-id suffix
- `host_label`

Disallowed review leakage:

- API key
- API secret
- raw signature
- raw auth header

## 14. Rollback and stop posture

If the first real-wire attempt behaves unexpectedly, the immediate safe posture is:

1. stop issuing new real testnet commands
2. switch executor mode back away from `real`
3. review `/ops -> /commands -> /commands/[id]`
4. preserve the evidence; do not rewrite it
5. do not patch replay behavior ad hoc in the same round

Practical rollback target:

```text
return to mock-only executor mode
while preserving all current preflight logic
```

## 15. Minimum test plan before real credential use

Before real credential-backed execution is even attempted, code should still prove locally:

1. `mock` mode continues to pass
2. unknown mode does not silently go real
3. `real` mode still refuses if preflight fails
4. normalized success/failure shapes are preserved when helper is mocked at the transport edge

This keeps the last offline safety net intact.

## 16. Review acceptance for this plan

This planning round is complete once the team can answer:

- which files own the real-wire change?
- how do we switch between `mock` and `real` safely?
- what must remain unchanged from preflight and mocked semantics?
- what evidence proves real-wire success vs failure?
- how do we immediately step back if the first real request is suspicious?

That answer is fixed by this document.

## 17. Next recommended round

Next recommended round:

```text
Real Testnet Real Wire Guarded Implementation V1
```

That round may start code again, but it should still begin with guard rails and mode switching before any real credential-backed request is actually allowed to run.

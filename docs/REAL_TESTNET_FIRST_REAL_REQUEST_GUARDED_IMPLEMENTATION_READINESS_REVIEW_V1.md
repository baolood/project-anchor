# Real testnet first real request guarded implementation readiness review V1

**Status:** readiness review only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** reconnect the now-complete review-artifact mini-bundle to the guarded real-request implementation path, and state what is already implemented, what is still blocked, and what the smallest next non-doc slice should be before the first bounded real external testnet request.

Canonical path only:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This review does not authorize the first real request. It only answers whether the repo is ready to leave docs-only work and where the next concrete guarded implementation slice should start.

## 1. Decision

Project Anchor is now in this posture:

```text
review-artifact docs: sufficiently complete
guarded implementation boundary: partially implemented
first real request: still BLOCKED
```

Meaning:

- the review and evidence side is no longer the main unknown
- the next blocker is no longer “how do we document it?”
- the next blocker is “what exact guarded code change still stands between real mode and one bounded real request?”

## 2. What is already implemented in code

The guarded testnet execution path already has several critical pieces in place.

### A. Canonical path and mode split exist

Current code already distinguishes:

- `TESTNET_EXECUTOR_MODE=mock`
- `TESTNET_EXECUTOR_MODE=real`
- invalid mode -> fail-closed
- unset mode -> not implemented / not real

This means accidental silent drift into real mode is already partially contained.

### B. Preflight boundary already exists

Current runner behavior already enforces guarded preflight families before any real transport:

- `KILL_SWITCH_ON`
- `TESTNET_BASE_URL_INVALID`
- `TESTNET_CREDENTIALS_MISSING`
- `TESTNET_CONTRACT_REJECTED` where relevant

This is a strong prerequisite because the first real request should not need to invent new preflight semantics.

### C. Mocked external-attempt event family already exists

Current mocked executor path already exercises:

- `TESTNET_EXECUTOR_REQUESTED`
- `TESTNET_EXECUTOR_ACCEPTED`
- `TESTNET_EXECUTOR_REJECTED`
- `ACTION_OK / MARK_DONE`
- `ACTION_FAIL / MARK_FAILED`

This means the target evidence shape for real mode is already known and test-backed.

### D. Real helper boundary already exists, but remains fail-closed

`anchor-backend/app/executors/testnet_order_executor.py` already has a dedicated real helper boundary.

Current real-mode outcomes are still intentionally:

- `TESTNET_REAL_WIRE_DISABLED`
- `TESTNET_REAL_WIRE_NOT_IMPLEMENTED`

with:

- `external_request_started=false`
- no `external_order_id`
- no signed HTTP

This is the correct current safety posture.

## 3. What is no longer the main blocker

The following areas are no longer the primary reason the first real request is blocked:

- review artifact format
- result label semantics
- synthetic examples for `BLOCKED / PASS / FAIL`
- artifact checklist
- reviewer notes quality guidance
- artifact maintenance/change-log discipline

Those areas now have enough structure to support the next step.

## 4. What still blocks the first real request

The first bounded real external request remains blocked by these concrete gaps.

### A. Real transport helper still does not send one bounded request

The current real helper has the boundary shape, but not the actual narrow outbound implementation.

That means the main missing piece is no longer conceptual. It is transport logic.

### B. No real-wire success/failure normalization has been proven from actual transport behavior

The mocked path proves event semantics, but not actual upstream normalization under:

- auth failure
- validation failure
- network error
- timeout
- accepted upstream response

### C. Runtime enablement is still intentionally one step short of real execution

This is correct, but it means the repo still cannot produce the first bounded real request even if an operator wanted to.

### D. No real request review artifact has yet been created from actual evidence

The synthetic mini-bundle is complete, but it has not yet been exercised against a real `command_id`.

## 5. Smallest next non-doc slice

The smallest safe next slice should be:

```text
implement one bounded real transport call in the real helper
without changing preflight semantics
without changing event names
without adding retry
without widening beyond canonical ORDER testnet
```

Primary write scope should remain:

- `anchor-backend/app/executors/testnet_order_executor.py`
- `anchor-backend/app/actions/runner.py`
- `anchor-backend/tests/test_testnet_external_executor_v1.py`
- one small new real-wire-focused backend test file if needed

Still out of scope:

- frontend
- deploy changes
- docker compose changes
- live executor
- retry/replay implementation
- legacy QUOTE path promotion

## 6. Acceptance for the next implementation slice

The next guarded implementation slice should not be treated as complete unless it proves all of these:

- real mode still requires explicit runtime enablement
- one bounded outbound request can happen only on canonical `ORDER + execution_mode=testnet`
- `TESTNET_EXECUTOR_REQUESTED` appears only when the boundary is actually crossed
- accepted upstream response normalizes into canonical success shape
- rejected/failed upstream response normalizes into approved failure families
- no secret leaks into result or event payload
- no retry is introduced
- retreat to `mock` or fail-closed posture remains immediate

## 7. Recommended immediate next round

The most natural next round after this review is:

```text
Real Testnet First Real Request Guarded Transport Implementation V1
```

Scope:

```text
small backend-only code slice
implement one bounded real transport path inside the existing guarded helper,
preserve current preflight and evidence semantics,
and keep live trading NO-GO
```

## 8. Stable status statement

At this point the correct status summary is:

```text
dry-run chain: PASS
mocked testnet external boundary: PASS
review-artifact mini-bundle: COMPLETE
guarded real helper boundary: PRESENT but still non-transport
first bounded real request: BLOCKED pending guarded transport implementation
live trading: NO-GO
```

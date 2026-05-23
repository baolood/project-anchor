# Real testnet first external executor plan V1

**Status:** implementation plan only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-23

**Scope:** define the smallest safe code slice that may follow the completed preflight-only boundary for the canonical future path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement the slice. It only fixes the exact plan for the first real external testnet request path.

## 1. Decision

The next code slice, after preflight-only V1, should be:

```text
one canonical real external testnet request path
with normalized success/failure evidence
and no automatic retry
```

That means:

- keep canonical `ORDER + execution_mode=testnet`
- keep preflight gates already implemented
- add the smallest possible real external request boundary after preflight passes
- normalize `REQUESTED / ACCEPTED / REJECTED`
- preserve negative evidence when upstream was not reached

Still not allowed in this slice:

- live trading
- automatic retry
- generic exchange abstraction expansion
- legacy `QUOTE + BINANCE_TESTNET` path reuse as the main implementation

## 2. Preconditions before this slice

This slice should begin only because these are already true:

- preflight-only boundary exists in code
- `KILL_SWITCH_ON`, `TESTNET_BASE_URL_INVALID`, `TESTNET_CREDENTIALS_MISSING` are normalized
- `/commands/[id]` can explain preflight refusal cleanly
- canonical env names and host-safety rules are already fixed in docs

This slice should not reopen those decisions.

## 3. Exact write scope

Primary write scope:

- `anchor-backend/app/actions/runner.py`
- `anchor-backend/app/workers/domain_command_worker.py`
- `anchor-backend/tests/test_testnet_boundary_preflight_v1.py`
- `anchor-backend/tests/test_testnet_external_executor_v1.py`

Optional new helper scope, only if a helper is clearly isolated:

- `anchor-backend/app/executors/testnet_order_executor.py`

Out of scope:

- frontend
- `anchor-console`
- deploy files
- docker compose
- risk rules
- live executor
- generic multi-venue expansion

## 4. Canonical flow for this slice

Target flow:

```text
ORDER testnet command
-> contract accepted
-> policy/risk accepted
-> kill switch checked
-> host safety checked
-> credential presence checked
-> TESTNET_EXECUTOR_REQUESTED
-> one signed external request
-> normalize upstream response
-> TESTNET_EXECUTOR_ACCEPTED or TESTNET_EXECUTOR_REJECTED
-> ACTION_OK or ACTION_FAIL
-> MARK_DONE or MARK_FAILED
```

Anything outside that flow is too large for this slice.

## 5. Runner ownership

`runner.py` should remain the boundary owner.

It should continue to:

- detect canonical `ORDER + execution_mode=testnet`
- perform preflight checks first
- stop locally if preflight fails
- create canonical event evidence
- normalize final result/error

New responsibility in this slice:

- after preflight passes, invoke one dedicated real testnet executor helper

Runner should not:

- directly manage long retry loops
- silently fallback to stub after request failure
- infer live vs testnet from anything except the canonical boundary inputs and env contract

## 6. Executor helper ownership

If a helper file is introduced, its responsibility should be narrow:

```text
given canonical normalized ORDER testnet input,
construct one signed testnet request,
send it,
parse it,
return normalized success or normalized failure
```

It should not:

- mutate DB rows directly
- emit final MARK_* events itself
- decide policy or risk
- decide kill switch
- retry automatically

The helper should return data back to runner for persistence and eventing.

## 7. Event plan

New event family expected in this slice:

```text
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_ACCEPTED
TESTNET_EXECUTOR_REJECTED
```

Required meaning:

- `TESTNET_EXECUTOR_REQUESTED`
  - canonical path crossed preflight
  - one real external request is about to be attempted or has just been initiated
- `TESTNET_EXECUTOR_ACCEPTED`
  - upstream returned a normalized success
  - `external_order_id` exists
- `TESTNET_EXECUTOR_REJECTED`
  - upstream attempt happened
  - normalized failure family explains the outcome

Must remain true:

- `TESTNET_EXECUTOR_STUB` stays stub-only
- preflight-only refusal must still avoid `REQUESTED`
- no event should pretend upstream contact happened when it did not

## 8. Success shape plan

The first real external success must normalize at least:

- `ok=true`
- `type=order`
- `execution_mode=testnet`
- `market`
- `symbol`
- `side`
- `notional`
- `order_type`
- `source`
- `created_by`
- `stop_price`
- `idempotency_key`
- `host_label`
- `external_order_id`
- `external_status`
- `ts`

If `external_order_id` is missing, the command must not be treated as canonical success.

## 9. Failure shape plan

The first real external failure must normalize at least:

- `ok=false`
- `execution_mode=testnet`
- `host_label`
- `failure_family`
- `failure_reason`
- `idempotency_key`
- `source`
- `created_by`
- `ts`

Candidate families in this slice:

- `TESTNET_EXECUTOR_AUTH_FAILED`
- `TESTNET_EXECUTOR_VALIDATION_FAILED`
- `TESTNET_EXECUTOR_REJECTED`
- `TESTNET_EXECUTOR_TIMEOUT`
- `TESTNET_EXECUTOR_NETWORK_ERROR`
- `TESTNET_EXECUTOR_UNEXPECTED`

Preflight families remain separate and must not be blurred into upstream failure.

## 10. Negative evidence rules

This slice must preserve these distinctions:

### If preflight fails

- no `TESTNET_EXECUTOR_REQUESTED`
- no `TESTNET_EXECUTOR_ACCEPTED`
- no `external_order_id`

### If upstream request happens and fails

- `TESTNET_EXECUTOR_REQUESTED` must exist
- `TESTNET_EXECUTOR_REJECTED` should exist
- `ACTION_FAIL` and `MARK_FAILED` should follow
- `external_order_id` may still be absent, depending on failure family

### If upstream request succeeds

- `TESTNET_EXECUTOR_REQUESTED` exists
- `TESTNET_EXECUTOR_ACCEPTED` exists
- `external_order_id` exists
- `ACTION_OK` and `MARK_DONE` follow

These distinctions are mandatory for `/commands/[id]` review.

## 11. Test plan

New test file:

```text
anchor-backend/tests/test_testnet_external_executor_v1.py
```

Recommended cases:

1. preflight pass + mocked upstream success
   - emits `REQUESTED -> ACCEPTED -> ACTION_OK -> MARK_DONE`
   - persists `external_order_id`
2. preflight pass + mocked auth rejection
   - emits `REQUESTED -> REJECTED -> ACTION_FAIL -> MARK_FAILED`
   - failure family = `TESTNET_EXECUTOR_AUTH_FAILED`
3. preflight pass + mocked timeout
   - emits `REQUESTED -> REJECTED -> ACTION_FAIL -> MARK_FAILED`
   - failure family = `TESTNET_EXECUTOR_TIMEOUT`
4. regression case proving preflight failure still emits no `REQUESTED`

The tests should remain offline and deterministic by mocking the executor helper.

## 12. Why this slice should still avoid automatic retry

Automatic retry remains too risky here because:

- first-attempt idempotency semantics are not yet exercised under real external pressure
- timeout vs accepted-late ambiguity is still sensitive
- replay evidence rules are already defined but not yet battle-tested in code

So this slice should do:

```text
single attempt only
```

and leave replay for a later bounded round.

## 13. Review acceptance for this slice

This slice should only be considered complete if:

- canonical `ORDER + execution_mode=testnet` is the only new main path
- preflight failures still look identical to current review semantics
- first external success has `external_order_id`
- first external failure families are normalized
- `/commands/[id]` can distinguish:
  - blocked before request
  - request attempted and failed
  - request attempted and succeeded
- no live host is touched

## 14. Recommended execution order

When this plan becomes code, safest order is:

1. add executor mock tests first
2. isolate executor helper contract
3. wire helper into runner after preflight pass
4. add event evidence
5. run backend unittest + baseline + go-live rules
6. inspect `/commands/[id]` semantics before expanding anything else

## 15. Next recommended round

Next recommended round:

```text
Real Testnet External Executor Mocked V1
```

That round may begin code again, but it should still stay offline by mocking the external request boundary before any real credential-backed integration.

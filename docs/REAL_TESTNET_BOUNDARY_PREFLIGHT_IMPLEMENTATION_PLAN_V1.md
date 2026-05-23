# Real testnet boundary preflight implementation plan V1

**Status:** implementation plan only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-23

**Scope:** map the already-approved first code slice onto exact backend write scope for the canonical future path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement the slice. It only fixes the smallest safe code plan for:

```text
boundary preflight validation only
```

## 1. Decision

The first code implementation must stay inside backend boundary-preflight logic and must stop before any signed HTTP.

Approved code target:

```text
canonical ORDER testnet boundary preflight
```

Approved proof targets:

- merged kill switch consumption
- host safety rejection
- canonical credential presence rejection
- normalized pre-external `TESTNET_*` failure family
- clear `/commands/[id]` evidence

Disallowed in this slice:

- exchange client creation
- signed request helpers
- external order creation
- live path reuse
- legacy `QUOTE + BINANCE_TESTNET` path expansion

## 2. Exact write scope

The implementation plan should touch only the backend files that own canonical order execution and its tests.

Primary write scope:

- `anchor-backend/app/actions/runner.py`
- `anchor-backend/app/workers/domain_command_worker.py`
- `anchor-backend/tests/test_testnet_boundary_preflight_v1.py`

Optional small helper write scope, only if needed to avoid duplicating constants:

- `anchor-backend/app/actions/runner.py` local helper section

Out of scope for this slice:

- frontend
- `anchor-console`
- deploy files
- docker compose
- risk rules
- real exchange client modules
- legacy quote executor behavior

## 3. Function-level plan

### A. `domain_command_worker.py`

Purpose:

```text
preserve canonical ORDER + execution_mode=testnet command routing
```

Planned changes:

- keep existing canonical `ORDER` routing intact
- ensure the action payload sent to runner keeps the canonical audit fields required by current contract:
  - `source`
  - `created_by`
  - `stop_price`
  - `idempotency_key`
- do not add any real external executor branch here

Expected outcome:

```text
worker still hands canonical testnet ORDER to runner
runner decides preflight PASS/FAIL
```

### B. `runner.py`

Purpose:

```text
host the first real-testnet boundary preflight gate
```

Planned changes:

- add a dedicated canonical preflight branch for:
  - `action == "order"`
  - `payload.execution_mode == "testnet"`
- in that branch, perform only these checks in order:
  1. canonical path identity sanity
  2. merged kill switch read
  3. host safety validation for `TESTNET_EXCHANGE_BASE_URL`
  4. credential presence validation for canonical `TESTNET_EXCHANGE_*`
  5. normalized local result shaping
- return a local result object that makes the refusal reviewable
- do not instantiate a real client
- do not sign requests
- do not create `external_order_id`

Required normalized failure families in this slice:

- `KILL_SWITCH_ON`
- `TESTNET_BASE_URL_INVALID`
- `TESTNET_CREDENTIALS_MISSING`
- optionally `TESTNET_CONTRACT_REJECTED` when a boundary-adjacent field is invalid at this layer

Required invariants:

- `execution_mode` remains `testnet`
- result is explicitly local/pre-external
- no `TESTNET_EXECUTOR_ACCEPTED`
- no `TESTNET_EXECUTOR_REQUESTED`
- no `TESTNET_EXECUTOR_STUB`

### C. New test file

Purpose:

```text
prove the first slice without any external side effect
```

Test file:

```text
anchor-backend/tests/test_testnet_boundary_preflight_v1.py
```

Planned cases:

1. kill switch ON -> command fails with `KILL_SWITCH_ON`
2. invalid testnet base URL -> command fails with `TESTNET_BASE_URL_INVALID`
3. missing canonical testnet credentials -> command fails with `TESTNET_CREDENTIALS_MISSING`
4. optional boundary-adjacent invalid field -> command fails with `TESTNET_CONTRACT_REJECTED`
5. negative evidence case proving:
   - no `external_order_id`
   - no executor-accepted event
   - no real signed HTTP helper invoked

## 4. Event and review evidence plan

The implementation should preserve the existing command-review chain and only add evidence that matches pre-external refusal.

Expected visible evidence family:

```text
PICKED
POLICY_ALLOW or POLICY_BLOCK when relevant
KILL_SWITCH_CHECKED when relevant
ACTION_FAIL
MARK_FAILED
```

Expected absent evidence:

```text
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_ACCEPTED
TESTNET_EXECUTOR_STUB
external_order_id
ACTION_OK
MARK_DONE
```

The implementation should make `/commands/[id]` answer these questions cleanly:

- was this canonical `ORDER + execution_mode=testnet`?
- which preflight gate stopped it?
- what normalized family was returned?
- did any external attempt happen?

## 5. Environment read plan

This slice should read only canonical runtime names:

- `TESTNET_EXCHANGE_BASE_URL`
- `TESTNET_EXCHANGE_API_KEY`
- `TESTNET_EXCHANGE_API_SECRET`
- `TESTNET_EXCHANGE_KEY_ID`

Rules:

- treat missing or blank credentials as `TESTNET_CREDENTIALS_MISSING`
- treat missing or invalid base URL as `TESTNET_BASE_URL_INVALID`
- do not fall back to legacy `BINANCE_*`
- do not use repo-file secrets
- do not accept payload-carried secrets

## 6. Kill-switch integration plan

The slice should consume only the shared merged kill-switch source.

Rules:

- do not re-read raw env in the executor branch
- do not build local override logic here
- fail closed if kill-switch state is unavailable or ON according to the chosen runtime rule
- emit review evidence that kill switch was checked when the branch reached that gate

## 7. What this slice must not do

Even if the code compiles and tests pass, the slice is not acceptable if it does any of these:

- constructs real exchange auth headers
- creates or stores `external_order_id`
- opens network connection
- reuses legacy `QUOTE + BINANCE_TESTNET` path as proof
- returns a fake upstream success shape
- emits success-only events for a blocked preflight result

## 8. Minimal acceptance handshake

The implementation is ready for review only if all of these are true:

- code diff stays inside the write scope above
- new tests are deterministic and offline
- local baseline stays green
- go-live rules stay green
- `/commands/[id]` semantics remain reviewable
- no new env naming drift appears

## 9. Recommended execution order

When this plan turns into code, the safest order is:

1. add tests that describe the preflight failures
2. add runner preflight branch
3. preserve worker routing and audit fields
4. run local unittest and baseline checks
5. inspect `/commands/[id]` evidence shape locally if exposed by existing tests

This keeps the first code slice narrow and auditable.

## 10. Not yet approved after this plan

Even after this plan is implemented successfully, these remain outside approval:

- real signed testnet request
- upstream auth exchange
- upstream validation failure shaping
- upstream timeout shaping under real HTTP
- operator replay against real external attempts
- any live trading path

## 11. Exit condition for this plan

This planning round is complete once the team can answer:

```text
which files will change,
which functions own preflight,
which tests prove it,
and what evidence must stay absent
```

That answer is now fixed by this document.

## 12. Next recommended round

Next recommended round:

```text
Real Testnet Boundary Preflight Implementation V1
```

That round may finally start code changes, but it should remain confined to the write scope defined here and still produce zero external side effects.

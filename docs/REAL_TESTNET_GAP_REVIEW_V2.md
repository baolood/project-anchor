# Real testnet gap review V2

**Status:** gap review only - not a real testnet enablement, not live trading approval.

**Owner:** **baolood** (Release / Engineering / Operations lead, interim).

**Date:** 2026-05-22

**Current posture:** the repository now has a stricter local `testnet stub` path, but it is still not ready for real exchange testnet execution.

## 1. Decision

Project Anchor is still **NO-GO** for real testnet execution.

What is ready:

```text
ORDER + execution_mode=testnet
-> local stub validation
-> local stub result
-> event semantics
-> review checklist
```

What is not ready:

```text
ORDER + real exchange testnet API
-> credential wiring
-> real external HTTP
-> kill switch proof at real executor boundary
-> smoke with real testnet response
```

## 2. What improved since V1

Compared with `docs/TESTNET_READINESS_GAP_REVIEW_V1.md`, the repo now has:

- a documented testnet command contract
- a documented testnet secrets custody plan
- a local `ORDER` testnet stub path
- success-only `TESTNET_EXECUTOR_STUB` semantics
- stricter stub field enforcement for:
  - `source`
  - `created_by`
  - `stop_price`
- a detailed runbook and a quick review checklist

That is solid pre-work. It still does not equal real testnet readiness.

## 3. Newly confirmed real-testnet gaps

### 3.1 Legacy `QUOTE` testnet path exists

The codebase still contains a legacy real testnet branch:

- [runner.py](/Users/baolood/Projects/project-anchor/anchor-backend/app/actions/runner.py:171)
- [binance_futures_testnet.py](/Users/baolood/Projects/project-anchor/anchor-backend/app/executors/binance_futures_testnet.py:14)

Current behavior:

```text
if EXECUTION_MODE=BINANCE_TESTNET and cmd_type=QUOTE
-> construct BinanceFuturesTestnetExecutor
-> read BINANCE_API_KEY / BINANCE_API_SECRET
-> call signed REST endpoints
```

Why this is a gap:

- it is `QUOTE`-shaped, not aligned with the newer `ORDER + execution_mode=testnet` contract
- it uses different env names than the newer secrets plan
- it is not tied to the stricter stub review path
- it creates two competing paths for “testnet”

Minimum next action:

```text
decide whether this legacy QUOTE path will be removed, isolated, or formally migrated
before any real testnet rollout
```

### 3.2 Credential naming is not aligned

Current docs prefer future names such as:

```text
TESTNET_EXCHANGE_API_KEY
TESTNET_EXCHANGE_API_SECRET
TESTNET_EXCHANGE_BASE_URL
```

But the legacy executor reads:

```text
BINANCE_API_KEY
BINANCE_API_SECRET
BINANCE_FUTURES_BASE
```

Why this matters:

- easy to wire the wrong key
- hard to prove “testnet-only” intent from env names alone
- creates confusion during review and incident response

Minimum next action:

```text
pick one canonical testnet env naming scheme before real testnet wiring
```

### 3.3 Real executor boundary is not yet proven for `ORDER`

Current `ORDER + execution_mode=testnet` path is a stub only:

```text
testnet_stub: true
external_call: false
```

That is good for safety, but it means the real executor boundary still lacks:

- real external request step
- explicit pre-call kill switch check evidence
- auth failure handling against a real upstream
- response normalization from a real exchange
- real smoke around retries/timeouts/network errors

Minimum next action:

```text
introduce a dedicated ORDER testnet executor boundary before any real key is used
```

### 3.4 Kill switch proof is still stub-level, not upstream-level

Current docs correctly require kill switch before external call, but there is not yet evidence that:

- a real testnet call is blocked when kill switch turns on
- a claimed command fails safe before signed HTTP is sent
- the event chain clearly distinguishes:
  - `KILL_SWITCH_ON`
  - contract rejection
  - upstream auth/network failure

Minimum next action:

```text
design a real testnet smoke that proves kill switch blocks the external executor boundary
```

### 3.5 No accepted real-testnet smoke exists yet

There is no committed smoke that proves:

- credentials are loaded safely
- a real testnet HTTP request is made
- a real exchange testnet response is recorded
- command detail review shows real testnet evidence

The accepted smoke today is still the dry-run smoke, not real testnet.

Minimum next action:

```text
write a real-testnet smoke spec before implementing real-key execution
```

## 4. Real testnet acceptance gates still missing

Real testnet should remain blocked until all of these are true:

```text
single canonical testnet execution path exists
ORDER contract is the chosen path
credential names are canonical
credentials are stored outside git
withdrawal disabled is verified
kill switch proof exists at real executor boundary
real testnet smoke exists
command detail shows real testnet evidence
R-001 remains understood and accepted
R-002 remains understood and accepted
live trading still NO-GO
```

## 5. Recommended next bounded rounds

Proceed in this order:

1. **Legacy Testnet Path Decision V1**
   Decide the fate of `EXECUTION_MODE=BINANCE_TESTNET + QUOTE`.

2. **Canonical Testnet Env Contract V1**
   Pick one naming scheme and document exact variable names.

3. **ORDER Testnet Executor Boundary V1**
   Add a dedicated real executor boundary for `ORDER`, still disabled by default.

4. **Real Testnet Smoke Spec V1**
   Define the exact PASS/FAIL evidence before any key is used.

5. **Kill Switch Real Boundary Check V1**
   Prove kill switch stops real testnet executor attempts before signed HTTP.

## 6. What not to do next

- Do not wire real testnet keys into the current repo just because the stub path is clean.
- Do not silently reuse the legacy `QUOTE` path and call that “real testnet ready”.
- Do not mix old env names and new env names.
- Do not skip the kill switch proof.
- Do not treat a successful local stub as upstream readiness.
- Do not interpret CI green as approval for real testnet.

## 7. Acceptance for this review

```text
stub vs real-testnet gap made explicit: PASS
legacy QUOTE testnet path called out: PASS
env naming mismatch called out: PASS
ORDER real-executor gap called out: PASS
kill switch real-boundary gap called out: PASS
real smoke missing called out: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

## 8. Next single task

Recommended next task:

```text
Legacy Testnet Path Decision V1
```

Scope:

- docs only
- decide what to do with the existing `QUOTE + BINANCE_TESTNET` branch
- no real key
- no external API call
- no live trading

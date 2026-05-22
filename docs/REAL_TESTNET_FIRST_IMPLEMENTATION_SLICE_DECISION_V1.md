# Real testnet first implementation slice decision V1

**Status:** implementation-slice decision only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** choose the safest first code slice after the current real-testnet readiness docs stack for the canonical future path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement the slice. It only decides which slice should come first and which ones must wait.

## 1. Decision

The first approved implementation slice is:

```text
canonical boundary preflight validation only
```

More specifically:

```text
host-safety validation
credential-presence gate
merged kill-switch consumption at boundary
normalized TESTNET_* failure outcomes
no signed HTTP
```

This first slice must **not** include:

```text
real external request
real testnet auth exchange
automatic retry
live trading
```

## 2. Why this slice wins

This slice is the safest first code step because it exercises the future executor boundary shape without crossing into real upstream side effects.

It gives us useful proof for:

- host safety enforcement
- credential handoff enforcement
- kill switch source-of-truth enforcement
- normalized failure families
- `/commands/[id]` review evidence

without needing:

- real credentials in active use
- external network side effects
- unresolved retry/replay semantics

## 3. What this slice should do

The first slice should accept canonical `ORDER + execution_mode=testnet` input and then:

1. confirm canonical path identity
2. consume merged kill switch state
3. validate host safety against named venue allowlist
4. validate canonical credential presence contract
5. normalize failure if any preflight gate fails
6. stop before any signed HTTP

This gives us a “real-boundary preflight” without real outbound execution.

## 4. Why not start with signed external request

Starting with real external request would be riskier because these areas are not all fully proven yet:

- replay semantics
- timeout/retry implementation behavior
- first-use credential runtime handling under real pressure
- accepted success/failure evidence consistency

The first slice should reduce uncertainty, not expand it.

## 5. Required boundaries for slice V1

The first implementation slice must preserve all of these:

- canonical path only: `ORDER + execution_mode=testnet`
- no legacy `QUOTE` branch reuse as the primary implementation
- no live host usage
- no repo-file secret handoff
- no payload-carried secret
- no automatic retry
- no real signed HTTP

If any of those would be crossed, the slice is too large.

## 6. Expected outcomes from slice V1

The slice should allow us to prove these failure paths cleanly:

- `KILL_SWITCH_ON`
- `TESTNET_BASE_URL_INVALID`
- `TESTNET_CREDENTIALS_MISSING`
- optionally `TESTNET_CONTRACT_REJECTED` where boundary-adjacent fields are missing

It should not yet try to prove:

- `TESTNET_EXECUTOR_AUTH_FAILED`
- `TESTNET_EXECUTOR_VALIDATION_FAILED`
- `TESTNET_EXECUTOR_REJECTED`
- `TESTNET_EXECUTOR_TIMEOUT`
- `TESTNET_EXECUTOR_NETWORK_ERROR`
- canonical external success

Those belong to later slices that actually cross the real request boundary.

## 7. Why this slice is still valuable

Even without real outbound execution, this slice would prove:

- the future executor boundary exists in code
- review-facing failure semantics are stable
- host safety rule is enforceable
- credential handoff rule is enforceable
- kill switch source rule is enforceable

That is real progress because it turns several docs decisions into one controlled, testable boundary.

## 8. Slice V1 inputs

The first slice should operate on canonical normalized inputs such as:

```text
command_id
attempt
execution_mode=testnet
market
symbol
side
order_type
stop_price
source
created_by
idempotency_key
```

It should read only canonical runtime names:

```text
TESTNET_EXCHANGE_API_KEY
TESTNET_EXCHANGE_API_SECRET
TESTNET_EXCHANGE_BASE_URL
TESTNET_EXCHANGE_KEY_ID
```

and the shared merged kill-switch state.

## 9. Slice V1 review evidence

The slice should be considered successful only if `/commands/[id]` can show:

- canonical path identity
- `KILL_SWITCH_CHECKED` where relevant
- normalized failure family when blocked
- no `TESTNET_EXECUTOR_ACCEPTED`
- no `external_order_id`
- no ambiguity about whether real external request happened

In other words:

```text
review must clearly show "boundary preflight blocked or allowed"
without pretending upstream contact occurred
```

## 10. Slice V1 test posture

The first slice should be testable locally or in isolated test mode with:

- no real key values
- no external API access
- deterministic failure expectations

Good first checks:

- kill switch ON => `KILL_SWITCH_ON`
- invalid host => `TESTNET_BASE_URL_INVALID`
- missing credential env => `TESTNET_CREDENTIALS_MISSING`

## 11. What waits for slice V2+

Only after slice V1 is stable should later slices consider:

- signed external request path
- upstream auth failure shaping
- upstream validation failure shaping
- timeout behavior under real request
- operator replay after real timeout
- canonical success result from real upstream

This preserves a gradual risk ladder.

## 12. Rejected first-slice options

These were considered but rejected as the first slice:

### Option A. Start with real signed request path

Rejected because:

- too many unresolved variables at once
- mixes credential/runtime/external issues immediately

### Option B. Start with retry/replay logic

Rejected because:

- retry semantics depend on a stable first boundary
- duplicate-prevention proof should not precede basic boundary proof

### Option C. Start with legacy QUOTE path cleanup

Rejected as first slice because:

- useful, but not the most direct proof of the canonical ORDER boundary
- can be addressed after canonical boundary preflight exists

## 13. Relationship to open questions

This decision does not resolve all open questions. It deliberately chooses a slice that can move forward while still respecting them.

It depends most directly on:

- Q-002 host safety rule
- Q-003 kill switch source rule
- Q-009 credential handoff rule

It intentionally postpones full reliance on:

- Q-007 timeout/retry under real external attempt
- Q-008 replay after real timeout

## 14. Relationship to adjacent docs

This decision aligns with:

- [docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md](/Users/baolood/Projects/project-anchor/docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md)
- [docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md)
- [docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md)
- [docs/REAL_TESTNET_CREDENTIAL_HANDOFF_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_CREDENTIAL_HANDOFF_RULE_V1.md)
- [docs/REAL_TESTNET_TIMEOUT_POLICY_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_TIMEOUT_POLICY_RULE_V1.md)
- [docs/REAL_TESTNET_IDEMPOTENCY_REPLAY_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_IDEMPOTENCY_REPLAY_RULE_V1.md)

## 15. Recommended next bounded round

After this decision, the natural next round is:

```text
Real Testnet Boundary Preflight Acceptance V1
```

Scope:

```text
docs-only
define exact PASS/FAIL acceptance for the preflight-only implementation slice
no real key
no live trading
```

## 16. Acceptance for this decision

```text
first implementation slice fixed to boundary preflight only: PASS
real signed HTTP explicitly deferred: PASS
host/credential/kill-switch gates prioritized: PASS
legacy QUOTE path not chosen as first slice: PASS
review evidence expectations stated: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

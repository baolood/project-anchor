# Real testnet boundary preflight acceptance V1

**Status:** acceptance spec only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** define the exact PASS/FAIL acceptance for the first approved implementation slice:

```text
canonical boundary preflight validation only
```

Canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement the slice. It defines what must be true before that preflight-only boundary is accepted as complete.

## 1. Decision

The first implementation slice is accepted only if it proves:

```text
canonical ORDER testnet boundary exists in code
host safety is enforced
credential presence is enforced
merged kill-switch state is enforced
normalized TESTNET_* failure results are reviewable
no signed HTTP is sent
```

Anything that crosses into real external request is out of scope for this acceptance.

## 2. What this slice is allowed to prove

This slice may prove only pre-external boundary behavior.

Valid proof targets:

- `KILL_SWITCH_ON`
- `TESTNET_BASE_URL_INVALID`
- `TESTNET_CREDENTIALS_MISSING`
- optionally `TESTNET_CONTRACT_REJECTED` for boundary-adjacent fields

This slice must not claim proof for:

- `TESTNET_EXECUTOR_AUTH_FAILED`
- `TESTNET_EXECUTOR_VALIDATION_FAILED`
- `TESTNET_EXECUTOR_REJECTED`
- `TESTNET_EXECUTOR_TIMEOUT`
- `TESTNET_EXECUTOR_NETWORK_ERROR`
- canonical real upstream success

## 3. Required implementation boundaries

The implementation is acceptable only if all of these remain true:

- canonical path is `ORDER + execution_mode=testnet`
- no legacy `QUOTE` path is reused as the main boundary
- no signed HTTP occurs
- no external order identifier is created
- no live host is contacted
- no repo-file secret handoff is used
- no payload-carried secrets are accepted

If any of these are violated, slice acceptance is `FAIL`.

## 4. Required review evidence

For every accepted preflight outcome, `/commands/[id]` must make these answers visible:

- was this the canonical `ORDER + execution_mode=testnet` path?
- which preflight gate failed?
- what normalized failure family was produced?
- was there any external request?
- was kill switch checked where relevant?

If command detail cannot answer those cleanly, acceptance is `FAIL`.

## 5. PASS scenarios

At minimum, slice acceptance requires all of these scenarios to pass.

### Scenario A. Kill switch ON

Input posture:

- canonical ORDER testnet command
- kill switch authoritative merged state = ON

Expected outcome:

- final state: `FAILED`
- family: `KILL_SWITCH_ON`
- event family includes `KILL_SWITCH_CHECKED`
- no `TESTNET_EXECUTOR_ACCEPTED`
- no `external_order_id`
- no signed HTTP

### Scenario B. Invalid testnet base URL

Input posture:

- canonical ORDER testnet command
- kill switch OFF
- invalid or non-allowlisted `TESTNET_EXCHANGE_BASE_URL`

Expected outcome:

- final state: `FAILED`
- family: `TESTNET_BASE_URL_INVALID`
- no `TESTNET_EXECUTOR_ACCEPTED`
- no `external_order_id`
- no signed HTTP

### Scenario C. Missing credential env family

Input posture:

- canonical ORDER testnet command
- kill switch OFF
- host safety passes
- missing or unusable canonical `TESTNET_EXCHANGE_*` credential env

Expected outcome:

- final state: `FAILED`
- family: `TESTNET_CREDENTIALS_MISSING`
- no `TESTNET_EXECUTOR_ACCEPTED`
- no `external_order_id`
- no signed HTTP

### Scenario D. Boundary-adjacent contract rejection

Input posture:

- canonical ORDER testnet command
- one required boundary field missing or invalid

Expected outcome:

- final state: `FAILED`
- family: `TESTNET_CONTRACT_REJECTED`
- no `TESTNET_EXECUTOR_ACCEPTED`
- no `external_order_id`
- no signed HTTP

This scenario is recommended, even if contract validation is partly covered elsewhere.

## 6. Required FAIL conditions

Acceptance must be marked `FAIL` if any of these happen:

- any scenario sends real signed HTTP
- any scenario produces `external_order_id`
- kill switch proof is ambiguous
- host safety failure does not normalize to `TESTNET_BASE_URL_INVALID`
- missing credential failure does not normalize to `TESTNET_CREDENTIALS_MISSING`
- command detail cannot distinguish preflight failure from external failure
- legacy `QUOTE` path evidence appears

## 7. Event-family requirements

Accepted preflight scenarios must produce event evidence consistent with local refusal, for example:

```text
PICKED
POLICY_ALLOW or POLICY_BLOCK when relevant
KILL_SWITCH_CHECKED when boundary-relevant
ACTION_FAIL
MARK_FAILED
```

These must **not** appear in accepted preflight-only results:

```text
TESTNET_EXECUTOR_ACCEPTED
ACTION_OK
MARK_DONE as proof of preflight success
```

`TESTNET_EXECUTOR_REQUESTED` should also be absent for pure preflight refusal scenarios, because no external request should begin.

## 8. Non-secret evidence rule

Accepted slice results must remain non-secret.

Review evidence may include:

- host label
- key id suffix or safe key id
- normalized failure family
- attempt number

Review evidence must not include:

- API key
- API secret
- request signature
- raw authorization header

If sensitive material appears, acceptance is `FAIL`.

## 9. Preflight success meaning

For this slice, “success” means:

```text
the boundary preflight logic behaves correctly
```

It does **not** mean:

- external request happened
- real testnet auth succeeded
- upstream accepted anything

This is important because preflight slice acceptance is about gate correctness, not external connectivity.

## 10. Operator recording format

Recommended recording shape:

```text
[Real Testnet Boundary Preflight Acceptance V1]

kill switch scenario: PASS/FAIL
invalid host scenario: PASS/FAIL
missing credential scenario: PASS/FAIL
contract rejection scenario: PASS/FAIL
no signed HTTP across all scenarios: PASS/FAIL
no external_order_id across all scenarios: PASS/FAIL
canonical ORDER path only: PASS/FAIL
review evidence visible at /commands/[id]: PASS/FAIL
live trading: NO-GO
overall: PASS/FAIL
```

## 11. Relationship to later slices

Only after this acceptance is clean should later slices attempt:

- real signed external request
- upstream auth failure shaping
- timeout under real request
- replay after timeout
- canonical real upstream success

This keeps the risk ladder intact.

## 12. Relationship to adjacent docs

This acceptance spec aligns with:

- [docs/REAL_TESTNET_FIRST_IMPLEMENTATION_SLICE_DECISION_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_IMPLEMENTATION_SLICE_DECISION_V1.md)
- [docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md](/Users/baolood/Projects/project-anchor/docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md)
- [docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md)
- [docs/REAL_TESTNET_CREDENTIAL_HANDOFF_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_CREDENTIAL_HANDOFF_RULE_V1.md)
- [docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md)

## 13. Recommended next bounded round

After this acceptance spec, the natural next round is:

```text
Real Testnet Boundary Preflight Implementation Plan V1
```

Scope:

```text
docs-only
map the accepted preflight slice onto exact backend files and write scope
no real key
no live trading
```

## 14. Acceptance for this spec

```text
preflight-only PASS/FAIL scenarios fixed: PASS
no signed HTTP requirement explicit: PASS
no external_order_id requirement explicit: PASS
canonical ORDER path only requirement stated: PASS
review evidence requirements stated: PASS
non-secret evidence rule stated: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

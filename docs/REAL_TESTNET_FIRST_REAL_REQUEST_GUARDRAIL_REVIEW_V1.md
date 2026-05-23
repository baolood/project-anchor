# Real Testnet first real request guardrail review V1

**Status:** guardrail review only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-23

**Scope:** define the final operator-and-reviewer guardrails that must be satisfied before Project Anchor is allowed to send the first real external testnet request on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize the request. It fixes the final readiness review and immediate retreat posture that must exist first.

## 1. Decision

The first real testnet request must remain blocked unless a reviewer can say:

```text
the canonical path is in use,
preflight refusal behavior is still intact,
mock and real modes are distinguishable,
kill switch can still stop the path before signed HTTP,
and rollback to mock-only posture is immediate
```

If any one of those claims is weak or ambiguous, the first real request must not happen.

## 2. What this review is trying to prove

This review exists to answer one narrow question:

```text
if we deliberately flip from mock to real mode for one bounded request,
do we still know exactly how to stop, explain, and retreat?
```

This review is not:

- live trading approval
- a throughput test
- a retry/replay exercise
- a substitute for the later real testnet smoke

## 3. Preconditions that must already be true

The review is blocked unless all of these are already true:

- canonical testnet path remains `ORDER + execution_mode=testnet`
- legacy `QUOTE + BINANCE_TESTNET` path is not being used as the main route
- mocked external executor evidence is green in tests
- guarded real mode remains fail-closed by default
- real helper contract is fixed to normalized transport input/output
- `/commands/[id]` explains preflight-blocked vs external-attempt evidence
- kill switch authoritative source is the merged runtime state
- host safety remains exact-origin allowlist only
- timeout posture remains `single_attempt_v1`
- replay posture remains explicit operator replay only
- live trading remains `NO-GO`

## 4. Exact go/no-go review questions

The reviewer must be able to answer **yes** to every question below before the first real request is allowed:

1. Is the command shape canonical `ORDER + execution_mode=testnet`?
2. Are `source`, `created_by`, `stop_price`, and `idempotency_key` all present and reviewable?
3. Does the configured host map to the exact allowlisted HTTPS testnet origin?
4. Can the current runtime prove canonical `TESTNET_EXCHANGE_*` credential presence without exposing secrets?
5. Is `TESTNET_EXECUTOR_MODE` explicitly set, rather than inherited or left ambiguous?
6. Can `/commands/[id]` still distinguish:
   - preflight refusal
   - mocked external attempt
   - real external attempt
7. Can operators prove kill switch refusal still wins before signed HTTP?
8. Is there a one-step retreat back to `mock` or fail-closed posture if anything looks wrong?

If any answer is `no`, `unknown`, or "probably", result is:

```text
BLOCKED - do not send the first real request
```

## 5. Required operator setup for the first real request

The first real request must be intentionally narrow:

- one command only
- one known testnet venue/host label
- one unique idempotency key
- one explicit operator identity in `created_by`
- one explicit source such as `ops_manual`
- one bounded response window
- no automatic retry
- no concurrent batch

Recommended minimum posture:

```text
notional kept intentionally small
symbol already exercised in dry-run/testnet docs
kill switch ready and reviewed before submission
mock fallback path rehearsed first
```

## 6. Required positive evidence before send

Before the first real request, the review bundle should already contain evidence for all of these:

- `TESTNET_REAL_WIRE_DISABLED` still appears when real mode is selected but real wire is not explicitly enabled
- `TESTNET_EXECUTOR_MODE_INVALID` still fails closed for unknown mode
- mocked path still emits:
  - `TESTNET_EXECUTOR_REQUESTED`
  - `TESTNET_EXECUTOR_ACCEPTED` or `TESTNET_EXECUTOR_REJECTED`
- preflight failure families still remain:
  - `KILL_SWITCH_ON`
  - `TESTNET_BASE_URL_INVALID`
  - `TESTNET_CREDENTIALS_MISSING`
  - `TESTNET_CONTRACT_REJECTED` where relevant

This proves the system still knows how to say "no" clearly before it is allowed to say "try once".

## 7. Required negative evidence before send

The review fails if any of these are ambiguous:

- real mode can be reached by unset executor mode
- legacy path can still look like canonical success
- `TESTNET_EXECUTOR_STUB` can appear on a real-mode path
- a preflight refusal can still emit external-attempt evidence
- `external_order_id` can appear without `TESTNET_EXECUTOR_ACCEPTED`
- secrets can appear in result or event payload

These are hard blockers because they would make the first real request non-reviewable even if it "worked".

## 8. First anomaly retreat posture

If the first real request attempt shows any abnormal signal, the response must be immediate and conservative.

Minimum retreat posture:

```text
stop sending additional real-mode commands
return executor mode to mock or fail-closed posture
preserve the exact command_id and evidence chain
review /commands/[id] before any second attempt
do not patch behavior mid-flight
```

Examples of anomaly triggers:

- unexpected failure family
- missing `REQUESTED` / `ACCEPTED` / `REJECTED` evidence
- `external_order_id` shape mismatch
- `/commands/[id]` explanation disagrees with raw event chain
- host label or configured origin mismatch

## 9. Required reviewer output

The review outcome for this document must be one of:

### `PASS`

Only if:

- every precondition is satisfied
- every review question is answered `yes`
- retreat posture is clear and rehearsed
- live trading remains `NO-GO`

### `BLOCKED`

If:

- any precondition is missing
- any review question is ambiguous
- any negative evidence rule is violated
- operators cannot explain how to retreat immediately

### `FAIL`

If:

- a real request is sent without this review
- the system produces contradictory evidence
- the path crosses into behavior that cannot be explained or rolled back safely

## 10. Minimal next-step implication

If this review is `PASS`, the next implementation slice may move from:

```text
guarded real transport contract
```

to:

```text
first bounded real testnet request implementation
```

But only for one deliberately narrow request path, with rollback-to-mock preserved as the default retreat.

If this review is not `PASS`, no real request should be attempted.

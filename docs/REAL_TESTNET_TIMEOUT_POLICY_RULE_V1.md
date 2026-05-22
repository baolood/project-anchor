# Real testnet timeout policy rule V1

**Status:** timeout-policy rule only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Security lead, interim).

**Date:** 2026-05-22

**Scope:** define the first canonical timeout / retry / replay posture for the future real testnet executor path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement timeout handling. It fixes the safety-first posture future implementation must follow.

## 1. Decision

The first canonical timeout policy for real testnet execution is:

```text
single external attempt
no automatic retry after timeout
operator-driven replay only
```

This means:

- one bounded outbound attempt per command attempt
- timeout produces a normalized failure
- replay, if any, must be explicit and human-controlled

## 2. Why this rule wins

This rule is chosen because it is the safest posture for the first real external executor slice.

It is better than automatic retry because:

- idempotency semantics are not yet fully proven
- duplicate external intent is a bigger risk than delayed confirmation
- operator review is still the primary control plane

The goal is:

```text
first prove bounded external behavior,
then consider smarter retry later
```

## 3. Canonical timeout posture

The first implementation posture should be:

- send at most one real external request per command attempt
- wait for one bounded response window
- on timeout, normalize to `TESTNET_EXECUTOR_TIMEOUT`
- do not auto-retry in the same command attempt
- do not auto-spawn a second external attempt in the background

This posture remains in force until a later round explicitly changes it.

## 4. Timeout classification rule

If the real external attempt does not complete within the configured window, normalize as:

```text
failure_family = TESTNET_EXECUTOR_TIMEOUT
```

and review should still be able to infer:

- canonical path was used
- kill switch had already passed
- host safety had already passed
- an external attempt was made
- the attempt did not complete within policy

## 5. No automatic retry rule

The future executor must not automatically:

- re-send the request after timeout
- retry on another host
- retry with a slightly changed payload
- silently convert timeout into success polling

Why:

- replay semantics are not settled enough
- this would weaken auditability
- it could produce duplicate external orders if upstream actually accepted the first attempt

## 6. Operator replay rule

After a timeout, the only approved replay posture is:

```text
explicit operator decision
new review step
new command attempt or clearly tracked replay action
```

No hidden automatic replay is allowed.

If replay is later supported, the resulting evidence must still let reviewers answer:

- was this the first external attempt or a replay?
- what replay key ties it back to the earlier timeout?

## 7. Recommended timeout evidence

When timeout occurs, review should be able to see:

- final state: `FAILED`
- family: `TESTNET_EXECUTOR_TIMEOUT`
- command still tied to canonical `ORDER + execution_mode=testnet`
- host label
- idempotency key
- attempt number
- event family showing `TESTNET_EXECUTOR_REQUESTED`

Recommended event family:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_REJECTED
ACTION_FAIL
MARK_FAILED
```

The event name may still be `REJECTED` for taxonomy purposes, but the normalized failure family must remain `TESTNET_EXECUTOR_TIMEOUT`.

## 8. Timeout policy label rule

The event payload and/or result should expose a non-secret timeout policy label, for example:

```text
timeout_policy_label = single_attempt_v1
```

Purpose:

- tells reviewers which bounded rule was active
- helps later compare future policy changes without guessing

This should align with `TESTNET_EXECUTOR_REQUESTED` payload guidance.

## 9. Replay boundary rule

If an operator later decides to replay after timeout, the system must not pretend it was the same clean acceptance path.

Replay should be distinguishable by at least one of:

- new command attempt number
- explicit replay marker
- linked operator action

The first timeout rule does not prescribe the final replay implementation, but it forbids invisible retries.

## 10. What timeout must not mean

Timeout must not be interpreted as:

- success with delayed UI update
- proof that upstream rejected the request
- permission to retry automatically
- reason to weaken kill switch or host-safety checks

It means:

```text
we attempted external contact,
bounded wait expired,
human review is required before replay
```

## 11. Relationship to idempotency

This timeout policy is intentionally conservative because idempotency replay guarantees are not yet fully closed.

Until idempotency enforcement is settled, timeout handling must prefer:

```text
bounded stop + explicit replay
```

over:

```text
speculative retry
```

## 12. Relationship to adjacent docs

This rule aligns with:

- [docs/REAL_TESTNET_OPEN_QUESTIONS_REGISTER_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPEN_QUESTIONS_REGISTER_V1.md)
- [docs/REAL_TESTNET_FAILURE_SHAPE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_SHAPE_RULE_V1.md)
- [docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md)
- [docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md)

It resolves Q-007 at the first-policy level.

## 13. What not to do

- Do not auto-retry on timeout in the first implementation slice.
- Do not collapse timeout into generic rejection.
- Do not hide replay behind the same attempt evidence.
- Do not treat timeout as proof that nothing reached upstream.
- Do not introduce live-trading semantics into this policy.

## 14. Recommended next bounded round

After this rule, the natural next round is:

```text
Real Testnet Idempotency Replay Rule V1
```

Scope:

```text
docs-only
resolve how replay and duplicate-prevention evidence should work after timeout or operator replay
no real key
no live trading
```

## 15. Acceptance for this rule

```text
single-attempt no-auto-retry posture fixed: PASS
timeout normalizes to TESTNET_EXECUTOR_TIMEOUT: PASS
operator-driven replay only stated: PASS
timeout policy label requirement stated: PASS
hidden retry forbidden: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

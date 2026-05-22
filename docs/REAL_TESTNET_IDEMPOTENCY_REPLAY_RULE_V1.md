# Real testnet idempotency replay rule V1

**Status:** idempotency/replay rule only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Security lead, interim).

**Date:** 2026-05-22

**Scope:** define how replay and duplicate-prevention evidence must work for the future canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement replay handling. It fixes the first reviewable rules for idempotency and operator replay after timeout or manual retry.

## 1. Decision

The first canonical replay/idempotency posture is:

```text
one logical intent keeps one stable idempotency key
each external attempt must be distinguishable
replay is explicit, never hidden
duplicate-prevention evidence must be reviewable
```

This rule works together with:

- single external attempt per command attempt
- no automatic retry after timeout
- operator-driven replay only

## 2. Why this rule exists

Once timeout and replay enter the picture, the core review question becomes:

```text
was this a new logical intent,
or the same intent being replayed?
```

Without a clear rule, duplicate external action risk becomes hard to reason about.

## 3. Canonical identity layers

The future real testnet path must distinguish at least these three layers:

1. logical intent
2. command attempt
3. external request attempt

Meaning:

```text
logical intent = one user/system decision to place one testnet order intent
command attempt = one bounded execution attempt under command processing
external request attempt = one concrete outbound request effort
```

These layers must not be collapsed into one opaque counter.

## 4. Stable idempotency key rule

One logical intent must keep one stable `idempotency_key`.

That means:

- timeout does not create a brand-new logical key by default
- operator replay of the same intent keeps the same logical idempotency key
- a truly new order intent must use a new idempotency key

Why:

- preserves logical identity across replay
- helps reviewers tie timeouts and later replay back to the same intent

## 5. Replay marker rule

Because the logical idempotency key stays stable, replay must be distinguished by additional evidence.

At minimum, replay must be distinguishable by one or more of:

- incremented command attempt
- explicit replay marker
- explicit replay reason
- operator action reference

The system must not make a replay look like the first clean attempt.

## 6. Canonical replay evidence

For a replay after timeout or manual decision, review should be able to see:

- same logical `idempotency_key`
- new command attempt or explicit replay marker
- replay reason
- link to prior failure family when available

Recommended replay-safe fields:

```text
idempotency_key
attempt
replay_of_attempt
replay_reason
replay_requested_by
replay_ts
```

Not every field must exist in V1 implementation, but replay invisibility is not allowed.

## 7. No hidden duplicate rule

The future executor must not:

- silently replay after timeout
- silently issue a second outbound request under the same visible attempt
- mutate payload materially while pretending it is the same first attempt

If a second outbound request happens, review must be able to tell it happened.

## 8. External attempt evidence rule

Each real external attempt should be distinguishable in review-safe evidence.

Recommended review-safe indicators:

- `attempt`
- `event_ts`
- `timeout_policy_label`
- `idempotency_key_hash`
- optional request-attempt marker

This helps answer:

```text
how many times did we actually try to contact upstream for this logical intent?
```

## 9. Duplicate-prevention meaning

This rule does not yet require a final storage implementation, but it does require the review semantics to be fixed.

Minimum review meaning:

- same `idempotency_key` across replay => same logical intent
- new attempt marker => new execution attempt
- no new attempt marker => no acceptable proof of replay

If duplicate-prevention logic exists later, it must preserve these visible meanings.

## 10. Timeout relationship

This replay rule depends on the timeout rule:

- timeout alone does not justify auto-retry
- operator replay is a separate reviewed action
- replay must not overwrite the meaning of the original timeout

Reviewers must still be able to answer:

- which attempt timed out?
- which later attempt was a replay?
- did both belong to the same logical intent?

## 11. Success/failure relationship

This rule must work for both outcomes:

### If replay later succeeds

Review should show:

- same logical `idempotency_key`
- earlier failed/timeout attempt exists
- later accepted attempt is distinguishable

### If replay also fails

Review should show:

- same logical `idempotency_key`
- multiple attempts are distinguishable
- failure families are attributable per attempt

## 12. Operator review questions

At `/commands/[id]` or linked evidence, operators should be able to answer:

- is this the first attempt or a replay?
- does this replay belong to the same logical intent?
- what triggered the replay?
- who requested the replay?
- is there evidence of more than one external attempt?

If these answers are unavailable, replay evidence is too weak.

## 13. What not to do

- Do not create a new idempotency key for every replay by default.
- Do not keep the same visible attempt number across multiple external tries.
- Do not auto-replay after timeout.
- Do not hide replay reason.
- Do not let duplicate-prevention semantics stay implicit.

## 14. Relationship to adjacent docs

This rule aligns with:

- [docs/REAL_TESTNET_TIMEOUT_POLICY_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_TIMEOUT_POLICY_RULE_V1.md)
- [docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md)
- [docs/REAL_TESTNET_FAILURE_SHAPE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_SHAPE_RULE_V1.md)
- [docs/REAL_TESTNET_SUCCESS_SHAPE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_SUCCESS_SHAPE_RULE_V1.md)
- [docs/REAL_TESTNET_OPEN_QUESTIONS_REGISTER_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPEN_QUESTIONS_REGISTER_V1.md)

It resolves Q-008 at the first-policy level.

## 15. Recommended next bounded round

After this rule, the natural next round is:

```text
Real Testnet Credential Handoff Rule V1
```

Scope:

```text
docs-only
resolve how canonical TESTNET_EXCHANGE_* credentials are allowed to arrive at runtime
no real key
no live trading
```

## 16. Acceptance for this rule

```text
stable idempotency key across replay fixed: PASS
replay must be explicitly distinguishable: PASS
hidden duplicate external attempts forbidden: PASS
timeout-to-replay relationship stated: PASS
operator replay questions stated: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

# Real Testnet first controlled send real-fill rule V1

**Status:** real-fill rule only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

**Scope:** define how the synthetic templates and examples should transition to a real filled first-controlled-send review package for the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize a real controlled send.
It only defines what evidence qualifies as a real fill, what does not, when `NOT_COLLECTED` must be used, and when the correct conclusion remains `NO-GO`.

## 1. Decision

The project now has enough templates, examples, and review bundles that the next boundary must be explicit:

```text
what counts as a real filled first-controlled-send review package,
and what still counts as synthetic, incomplete, or blocked?
```

Without that rule, the project risks treating polished documentation as if it were runtime proof.

## 2. Fixed applicability

This rule applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be reused for:

- legacy `QUOTE + BINANCE_TESTNET`
- `TESTNET_EXECUTOR_STUB`
- dry-run commands
- live trading

## 3. What counts as `real-fill`

A first-controlled-send review package counts as `real-fill` only if all of these are true:

1. one real bounded runtime window existed
2. one real opened-window posture was recorded
3. one real runtime-verification step was recorded
4. one real controlled send was attempted or intentionally blocked inside that window
5. one real `/commands/[id]` evidence chain exists for that event, or an explicit `not-sent` explanation is documented
6. one real final review artifact is written using actual event facts, not example substitutions

In short:

```text
real-fill requires non-synthetic event identity plus non-synthetic review evidence
```

## 4. What does **not** count as `real-fill`

None of these count as real-fill by themselves:

- a copied synthetic example with names changed
- a completed template using guessed values
- a record that has no real `command_id` and no explicit justified `not-sent` explanation
- a file that says "looks like PASS" without matching `/commands/[id]` evidence
- a review package assembled only from expectations, not observed runtime facts
- a result inferred from memory after the fact

If the evidence must be imagined, summarized from memory, or reconstructed without bounded references, it is not real-fill.

## 5. Required identity markers for `real-fill`

A real-filled first-controlled-send package must be identifiable as real within a few lines.

It should include:

- actual review date
- actual operator
- actual reviewer
- actual host label
- actual runtime posture label
- actual `command_id`, or explicit `not-sent`
- actual `idempotency_key`
- actual result label

If a reader cannot tell whether the package is synthetic or real within a few lines, the package is invalid as real-fill.

## 6. When `NOT_COLLECTED` must be written

Use `NOT_COLLECTED` explicitly when a field should exist in principle but was not actually available at review time.

Examples:

- `/commands/[id]` was unreachable during the bounded window
- one correlation field was not captured before retreat
- a reviewer note could not confirm one expected surface
- a log excerpt was intentionally not preserved

The rule is:

```text
missing but expected -> write NOT_COLLECTED with reason
never replace it with a guess
```

## 7. When `NOT_COLLECTED` is not enough

`NOT_COLLECTED` does not automatically preserve acceptability.

If the missing field prevents the reviewer from determining:

- whether the send was actually attempted
- what final command state occurred
- what normalized family applied
- whether retreat was required
- whether a second request remains blocked

then the correct verdict cannot be upgraded by explanation alone.

That package should remain `BLOCKED` or `FAIL`.

## 8. When the correct conclusion is still `NO-GO`

The project remains `NO-GO` for live trading if any of these remain true:

- the first controlled send package is still synthetic
- the first controlled send evidence is incomplete in a way that hides the final state
- a real send was attempted but the evidence cannot be reconciled safely
- retreat posture was unclear or insufficient
- second-attempt pressure appears before the first package is fully reviewed and closed
- the review package cannot distinguish real facts from templates/examples

In short:

```text
real-fill is necessary for progress,
but real-fill does not equal live-trading approval
```

## 9. Minimal real-fill checklist

Use this checklist for one narrow question:

```text
is this package truly real-filled,
or is it still synthetic / incomplete / blocked?
```

Checklist:

- real runtime window existed: yes/no
- real opened-window record exists: yes/no
- real runtime-verification record exists: yes/no
- real attempt record exists or explicit not-sent rationale exists: yes/no
- `/commands/[id]` evidence exists or absence is explicitly bounded: yes/no
- result label is supported by observed evidence: yes/no
- synthetic/example material clearly separated: yes/no
- any missing fields marked `NOT_COLLECTED` with reason: yes/no
- package still `NO-GO` for live trading unless separately approved: yes/no

If any one of these is not a clean `yes`, the package is not fully real-filled.

## 10. Stable status statement

At this point the correct real-fill summary is:

```text
real-fill means one actual first-controlled-send review package
is populated from bounded non-synthetic runtime facts
missing expected evidence must be marked NOT_COLLECTED, never guessed
and live trading remains NO-GO unless separately approved
```

## 11. Minimal next bounded round

After this rule, the next natural bounded round is:

```text
Real Testnet First Controlled Send Real-Fill Checklist V1
```

Scope:

```text
docs-only
compress the real-fill rule into one short reviewer checklist
for deciding whether a first-controlled-send package is truly real-filled
```

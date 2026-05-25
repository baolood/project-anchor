# Real Testnet first controlled send real-fill checklist V1

**Status:** checklist only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

**Scope:** compress the real-fill rule into one short reviewer checklist for deciding whether a first-controlled-send package is truly real-filled on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This checklist does not authorize a real controlled send by itself.
It only checks whether the review package is truly populated from bounded non-synthetic runtime facts.

## 1. Use this checklist for one question only

Ask:

```text
is this first-controlled-send package truly real-filled,
or is it still synthetic, incomplete, or blocked?
```

Do not use this checklist as a substitute for:

- runtime-window authorization
- actual send approval
- kill-switch boundary review
- live-trading approval

## 2. Real event existence

Confirm all of these:

- one real bounded runtime window existed
- one real opened-window record exists
- one real runtime-verification record exists
- one real attempt record exists, or an explicit justified `not-sent` rationale exists

If any of these fail, real-fill review is `FAIL`.

## 3. Identity clarity

Confirm the package clearly shows:

- actual review date
- actual operator
- actual reviewer
- actual host label
- actual runtime posture label
- actual `command_id`, or explicit `not-sent`
- actual `idempotency_key`

If a reader cannot tell within a few lines whether the package is synthetic or real, real-fill review is `FAIL`.

## 4. Evidence coherence

Confirm all of these:

- `/commands/[id]` evidence exists, or its absence is explicitly bounded
- result label is supported by observed evidence
- final command state is supported by observed evidence
- normalized family is supported by observed evidence
- retreat posture, if relevant, is explained without guesswork

If the package relies on memory, inference, or “looks like,” real-fill review is `FAIL`.

## 5. `NOT_COLLECTED` rule

Confirm this rule was followed:

- any missing but expected field is marked `NOT_COLLECTED`
- each `NOT_COLLECTED` field has a reason
- no missing field was replaced by a guess

If a missing field was guessed instead of marked, real-fill review is `FAIL`.

## 6. When `NOT_COLLECTED` is insufficient

If a missing field prevents the reviewer from determining:

- whether the send was actually attempted
- what final command state occurred
- what normalized family applied
- whether retreat was required
- whether a second request remains blocked

then the package cannot be treated as fully real-filled.

Result: `FAIL`.

## 7. Synthetic separation

Confirm all of these:

- synthetic examples remain obviously synthetic
- templates remain templates
- actual filled package is event-specific
- no example language is presented as runtime fact

If synthetic and real material are blurred, real-fill review is `FAIL`.

## 8. `NO-GO` preservation

Confirm the package still preserves:

- `NO-GO` for live trading unless separately approved
- no implication that real-fill equals live approval
- no implication that a second controlled send is preapproved

If the package weakens those boundaries, real-fill review is `FAIL`.

## 9. Minimal result

Use one of:

- `PASS` = package is truly real-filled, coherent, bounded, and still preserves `NO-GO`
- `FAIL` = package is synthetic, incomplete, contradictory, or unsafe to treat as real review evidence

This checklist does not use `BLOCKED` because it is evaluating the package, not the send decision.

## 10. Stable status statement

At this point the correct real-fill-checklist summary is:

```text
real-fill means a first-controlled-send review package
is populated from bounded non-synthetic runtime facts,
clearly separated from templates/examples,
with `NOT_COLLECTED` used instead of guesses,
and with live trading still NO-GO
```

## 11. Minimal next bounded round

After this checklist, the next natural bounded round is:

```text
Real Testnet First Controlled Send Real-Fill Closeout V1
```

Scope:

```text
docs-only
record that the real-fill decision layer is now complete,
and state exactly what still blocks non-synthetic first-controlled-send proof
from becoming an accepted reviewed event
```

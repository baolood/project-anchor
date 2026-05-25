# Real Testnet first controlled send actual artifact rule V1

**Status:** actual-artifact rule only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

**Scope:** define how an actual first-controlled-send filled artifact should be named, stored, and distinguished from synthetic examples once a non-synthetic package finally exists for the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize a real controlled send.
It only defines how a real filled review artifact must appear once bounded non-synthetic evidence actually exists.

## 1. Decision

The project now has:

- synthetic examples
- maintenance rules
- change-log rules
- a real-fill decision layer

The next boundary must therefore be explicit:

```text
when a true non-synthetic first-controlled-send package exists,
how must the actual filled artifact be named, stored,
and kept distinct from examples and reusable guidance?
```

Without that rule, a future real artifact could be mixed with synthetic materials or made hard to trust.

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

## 3. What counts as an actual artifact

An actual first-controlled-send artifact is a review record that is populated from one bounded non-synthetic event.

It should correlate to:

- one actual review date
- one actual operator
- one actual reviewer
- one actual host/runtime posture
- one actual `command_id`, or one explicit justified `not-sent` bounded event

If those anchors do not exist, the file is not an actual artifact.

## 4. Required storage location

An actual first-controlled-send filled artifact should live under:

```text
docs/reviews/real_testnet/
```

It should not be stored:

- next to reusable templates in `docs/`
- inside backend source trees
- inside frontend source trees
- in ad hoc scratch locations

The artifact home remains the dedicated review-artifact directory because that directory already carries the non-secret and classification rules.

## 5. Required naming rule

Use filenames shaped like:

```text
FIRST_CONTROLLED_SEND_<date>_<command_id-or-not-sent>.md
```

Examples:

- `FIRST_CONTROLLED_SEND_2026-05-25_order-abc123.md`
- `FIRST_CONTROLLED_SEND_2026-05-25_not-sent-blocked.md`

Rules:

- include the real review date
- include the real `command_id`, or an explicit bounded `not-sent` suffix
- never use synthetic markers such as `example-pass`
- never include secrets in the filename

If the filename still looks like an example, it is not acceptable as an actual filled artifact.

## 6. Required distinction from synthetic examples

An actual filled artifact must be distinguishable from a synthetic example within a few lines.

It should clearly show:

- actual event date
- actual operator/reviewer identity
- actual or explicitly bounded `command_id`
- actual host label
- actual runtime posture
- actual result label

It must not:

- reuse example-only suffixes
- retain placeholder wording
- use guessed fields copied from templates

If a reader must guess whether the file is real or synthetic, the artifact is invalid.

## 7. `not-sent` rule

An actual filled artifact may still be real even when no external attempt occurred, but only if:

- the bounded event really happened
- the package reflects actual runtime review facts
- the reason for `not-sent` is explicit
- the result label remains consistent with those facts

In short:

```text
real artifact does not require external attempt
but it does require a real bounded review event
```

## 8. Secret and mutation guardrail

Actual filled artifacts must remain non-secret.

Allowed:

- `command_id`
- `idempotency_key`
- `host_label`
- `configured_origin`
- normalized family
- final result label

Not allowed:

- API key
- API secret
- raw auth header
- request signature
- plaintext credential dumps

Also:

- the artifact may clarify or append, but must not rewrite history
- if later edits change meaning, the change-log rule applies

## 9. Minimal actual-artifact checklist

Use this checklist for one narrow question:

```text
does this file qualify as an actual first-controlled-send artifact?
```

Checklist:

- stored under `docs/reviews/real_testnet/`: yes/no
- filename uses `FIRST_CONTROLLED_SEND_<date>_<real-id-or-not-sent>`: yes/no
- clearly real, not synthetic: yes/no
- actual event identity present: yes/no
- actual or explicitly bounded `command_id` present: yes/no
- result label supported by observed facts: yes/no
- no secret material present: yes/no
- no placeholder/example wording left behind: yes/no

If any one of these is not a clean `yes`, the file is not acceptable as an actual artifact.

## 10. Stable status statement

At this point the correct actual-artifact summary is:

```text
once a non-synthetic first-controlled-send package exists,
its durable filled artifact must be stored under the review-artifact directory,
named as a real event, clearly distinguishable from examples,
and kept non-secret and non-rewritten
```

## 11. Minimal next bounded round

After this rule, the next natural bounded round is:

```text
Real Testnet First Controlled Send Actual Artifact Checklist V1
```

Scope:

```text
docs-only
compress the actual-artifact rule into one short reviewer checklist
for deciding whether a filled record is acceptable as true first-controlled-send evidence
```

# Cloud host future public surface separation rule V1

**Status:** surface separation rule only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define how a future stable operator-facing ingress should remain separated from any later broader workflow or customer-facing surfaces on the cloud host.

This rule does not authorize broader public ingress today.
It prevents a future operator ingress from quietly becoming an everything-ingress.

## 1. Decision

When broader stable ingress eventually becomes justified, the first durable operator ingress should remain distinct from any later workflow-facing or customer-facing surfaces.

Meaning:

- do not collapse operator review surfaces and broader product surfaces into one boundary by default
- do not let operator-control needs decide customer-facing exposure shape
- do not let customer-facing convenience weaken operator review posture

The correct future posture is layered separation, not shared surface sprawl.

## 2. What this rule is for

This rule exists to avoid a common later-stage mistake:

```text
once a stable ingress exists,
it becomes tempting to put every useful screen behind the same host boundary
```

That would blur the difference between:

- operator review and control surfaces
- bounded workflow execution surfaces
- future customer-facing or broader access surfaces

Those layers do not have the same risk profile and should not be treated as interchangeable.

## 3. Operator-facing surfaces should stay distinct

Operator-facing stable ingress should remain centered on review and control surfaces such as:

- `/ops`
- `/commands`
- `/commands/[id]`

These exist to support:

- command review
- evidence interpretation
- retreat decisions
- operator accountability

They should not be quietly redesigned into a general public workflow surface.

## 4. Future workflow-facing surfaces should be treated separately

Later workflow-facing candidates may include:

- Trade Gate UI
- bounded internal operational workflows
- future non-review submission or monitoring views

These should be considered a separate layer because they optimize for:

- workflow convenience
- repeated use
- narrower task completion patterns

That is different from the operator review layer, which optimizes for:

- evidence quality
- decision traceability
- incident handling
- retreat and control

## 5. Why separation matters

Without separation, the project risks:

- leaking operator-only assumptions into broader surfaces
- widening access to review/control surfaces too early
- coupling workflow UX changes to operator incident posture
- making it harder to reason about who should reach which host paths

The first stable ingress should improve clarity, not merge unlike responsibilities.

## 6. Minimum boundary rule

If a future stable ingress task is opened, the default assumption should be:

```text
operator review/control surfaces are one boundary
workflow-facing surfaces are another decision
customer-facing surfaces are a later and separate decision
```

No layer should be merged forward just because the prior layer already has a hostname.

## 7. What must remain true after future separation

Even in a later-stage system, all of these should remain true:

- operator review/control surfaces preserve explicit accountability
- raw runtime internals remain non-public
- review and retreat flows remain canonical
- broader workflow surfaces do not gain hidden runtime control powers
- a customer-facing path, if it ever exists, does not inherit operator-only assumptions by accident

## 8. What should not happen

Do not use a future stable operator ingress as an excuse to:

- expose `/ops` to broader non-operator traffic
- mix Trade Gate workflow pages with raw operator-control posture without a separate boundary decision
- let one reverse-proxy decision implicitly define every future surface
- blur review evidence surfaces and workflow convenience surfaces into the same permission expectation

If any of those happen, the surface plan is drifting.

## 9. Minimum success criteria for a later ingress split

A future surface-separation effort should not be considered successful unless:

- operator review/control surfaces remain explicit and bounded
- workflow-facing surfaces are intentionally chosen, not inherited by convenience
- broader public or customer-facing surfaces, if any, are introduced by separate decision
- evidence quality at `/commands/[id]` is not weakened by surface expansion

## 10. Stable status statement

At this point the correct surface-separation summary is:

```text
future durable operator ingress should stay review/control-specific
workflow-facing stable surfaces are a later and separate boundary question
customer-facing expansion is later still
domain remains deferred until after first-real-request proof
live trading: NO-GO
```

## 11. Minimal next bounded round

After this rule, the next natural host-related bounded round is:

```text
Cloud Host Operator Ingress Acceptance Rule V1
```

Scope:

```text
docs-only
define the minimum acceptance criteria a future durable operator ingress
would need before it could be considered a good replacement for tunnel-style access
```

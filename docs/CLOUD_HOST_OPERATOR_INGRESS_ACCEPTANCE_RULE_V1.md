# Cloud host operator ingress acceptance rule V1

**Status:** acceptance rule only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the minimum acceptance criteria a future durable operator ingress would need before it could be considered a good replacement for the current tunnel-style access posture.

This rule does not authorize building that ingress now.
It defines what “good enough to replace tunnel-style access” would mean later.

## 1. Decision

A future durable operator ingress should not be accepted just because it is easier to reach.

It should be accepted only if it preserves or improves all of these at the same time:

- operator review clarity
- retreat safety
- evidence quality
- boundary discipline

If a future ingress is more convenient but weaker on those dimensions, it is not a valid replacement.

## 2. What this rule is for

This rule exists because tunnel-style access is awkward but currently safe in one important sense:

```text
it is narrow
it is obviously operator-mediated
and it does not pretend to be a polished general entrypoint
```

A future stable ingress should not lose those safety properties just because it looks cleaner.

## 3. Minimum required capabilities

Before a future durable operator ingress could replace tunnel-style access, it should support all of these:

1. stable access to operator review surfaces
2. consistent access to `/ops`
3. consistent access to `/commands`
4. consistent access to `/commands/[id]`
5. preserved ability to inspect evidence during the first-real-request style review flow
6. no dependence on raw backend public exposure

If it cannot do those, it is not a real replacement.

## 4. Minimum required safety properties

The ingress must also preserve all of these safety properties:

- raw backend/runtime internals remain non-public
- operator-only surfaces do not become casually broad public surfaces
- runtime toggle mutation is not silently exposed
- ingress changes remain separable from execution proof
- retreat to `mock` or fail-closed posture remains possible without ingress rework

The future ingress is not acceptable if it increases reachability by weakening any of those boundaries.

## 5. Minimum required review properties

The ingress should be accepted only if it still supports the canonical review flow:

```text
/ops
-> /commands
-> /commands/[id]
```

And if operators can still clearly answer:

- what mode the system is in
- whether the command stayed in preflight refusal
- whether it stopped at the guarded real boundary
- whether it crossed into real external-attempt evidence
- whether retreat is required

If a stable ingress makes those answers harder, it is not an improvement.

## 6. Minimum required operational posture

The ingress should not replace tunnel-style access unless the operator can also say:

- host identity remains explicit
- revision/runtime posture remains explicit
- review surfaces are stable under the new ingress
- anomaly handling does not depend on widening access again
- the first-real-request evidence model still makes sense under the new path

This is important because ingress replacement is not just network plumbing.
It changes how people interpret the system.

## 7. What does **not** count as acceptance

The following are not enough by themselves:

- “the URL is nicer”
- “it opens faster”
- “it avoids using a tunnel”
- “it is easier for one person to reach”
- “it feels more production-like”

Those may be nice side effects, but they are not acceptance criteria.

## 8. Minimum negative evidence requirements

A future durable operator ingress should not be accepted if any of these become true:

- raw backend exposure becomes part of normal operator access
- `/ops` becomes mixed with broader non-operator traffic by default
- runtime toggles or low-level internals become easier to mutate accidentally
- review evidence becomes weaker or less trustworthy than under the current narrow posture
- a later workflow-facing surface quietly inherits operator-control assumptions

If any of these appear, the ingress is drifting in the wrong direction.

## 9. Acceptance checklist

Use this short checklist when evaluating a future durable operator ingress:

```text
stable_ops_reachable: yes/no
stable_commands_reachable: yes/no
stable_command_detail_reachable: yes/no
raw_backend_non_public: yes/no
runtime_toggle_mutation_non_public: yes/no
review_flow_preserved: yes/no
retreat_posture_preserved: yes/no
evidence_quality_preserved: yes/no
broader_surface_separation_preserved: yes/no
verdict: PASS/BLOCKED/FAIL
notes:
```

## 10. PASS criteria

This rule is `PASS` only if:

- review surfaces are durably reachable
- raw internals remain non-public
- retreat posture is at least as safe as before
- evidence quality is preserved
- operator-facing and broader future surfaces remain separated

## 11. BLOCKED criteria

This rule is `BLOCKED` if:

- ingress is more reachable but not clearly safer
- review flow is not proven under the new posture
- internal/runtime boundaries would blur
- broader surface separation is still unclear

This is a healthy stop.
It means the tunnel-style posture may still be the better bounded access model for now.

## 12. FAIL criteria

This rule is `FAIL` if:

- ingress replacement would widen raw runtime exposure
- review evidence would become weaker
- operator-only controls would become casually broader
- the new ingress would encourage network-boundary drift during execution proof

## 13. Stable status statement

At this point the correct acceptance summary is:

```text
a future durable operator ingress must beat tunnel-style access on clarity and safety,
not just convenience
raw internals must remain non-public
review and retreat quality must be preserved
domain remains deferred until after first-real-request proof
live trading: NO-GO
```

## 14. Minimal next bounded round

After this rule, the next natural host-related bounded round is:

```text
Cloud Host Operator Ingress Review Bundle V1
```

Scope:

```text
docs-only
collect the operator ingress plan, separation rule, domain gate, and acceptance rule
into one small bundle for future ingress decision review
```

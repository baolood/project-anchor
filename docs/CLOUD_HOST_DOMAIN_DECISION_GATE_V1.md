# Cloud host domain decision gate V1

**Status:** domain decision gate only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the exact conditions under which domain setup or broader public ingress work stops being premature for the cloud host and becomes an allowed, separately-bounded follow-up task.

This gate does not authorize a domain today.
It defines when asking for one would stop being the wrong next step.

## 1. Decision

Right now, domain work remains:

```text
premature
non-blocking
not the next bottleneck
```

Meaning:

- the cloud host does not yet need a public hostname to prove the current stage
- a domain would currently add surface area faster than it adds decision clarity
- domain work should remain gated behind concrete readiness proof, not desire for polish

## 2. What this gate is for

This gate exists because domain work is easy to mis-time.

Too early, a domain mostly adds:

- wider exposure expectations
- more operator burden
- more confusion between “reachable” and “ready”

The goal is to ensure domain work begins only when it serves a real operational need rather than visual completeness.

## 3. Conditions that must be true before domain work is allowed

Domain or broader public ingress work should remain out of scope until **all** of these are substantially true:

1. the first bounded real testnet request has been attempted under the canonical path
2. that request is fully reviewable through `/ops -> /commands -> /commands/[id]`
3. the result has been classified cleanly as `PASS`, `BLOCKED`, or `FAIL`
4. retreat posture has been proven credible if the first request did not go cleanly
5. ingress freeze discipline has already been maintained during the first-real-request window
6. the host is no longer relying mainly on ad hoc engineering-only access assumptions
7. there is a genuine need for a more durable external entrypoint

If any one of these remains weak, domain work is still premature.

## 4. What does **not** count as sufficient reason

The following are **not** sufficient by themselves:

- “it would be easier to remember”
- “it looks more complete”
- “we want a cleaner URL before the first real request”
- “it might help debugging”
- “we already know we’ll need one eventually”

Those are convenience reasons, not readiness reasons.

## 5. What **does** count as a valid trigger

Domain work becomes reasonable only when one or more of these become true **after** the first guarded real-request proof:

- operator review surfaces need a stable durable hostname
- reverse-proxy posture has become the chosen long-term access boundary
- tunnel-based access is no longer the intended steady-state operator pattern
- a bounded non-engineering user needs controlled access to stable review surfaces

Even then, domain work should still be a separate bounded task, not mixed into real-request proof.

## 6. Required evidence before opening a domain task

Before a domain/public-ingress task should be opened, the project should already be able to point to:

- first real request evidence bundle
- `/commands/[id]` review clarity
- ingress freeze compliance during the request window
- retreat drill and runtime verification materials
- a clear statement of which surfaces are still operator-only versus candidate future-public

Without those, the domain conversation is still too early.

## 7. What domain work must not be used to hide

A domain must not be used to paper over:

- weak host access discipline
- unclear operator review flow
- unstable runtime verification
- inability to review command evidence cleanly
- confusion about whether the host is engineering-only or operator-ready

If those problems exist, a domain would make the system look more ready than it is.

## 8. If the gate is not passed

If the gate is not passed, the correct response is:

```text
do not start domain work
continue on host/runtime/review proof
```

That is not lost momentum.
It is correct sequencing.

## 9. If the gate is passed

If the gate is passed, the next task should still be bounded and explicit, for example:

```text
Cloud Host Durable Operator Ingress Plan V1
```

or

```text
Cloud Host Domain Rollout Boundary V1
```

Meaning:

- decide which surfaces would actually get the hostname
- decide which surfaces remain operator-only
- keep raw backend/runtime internals non-public
- preserve reviewability and retreat posture

## 10. Stable status statement

At this point the correct domain-decision summary is:

```text
domain is not a current blocker
domain should wait until after first-real-request proof and review closure
operator/runtime boundary proof still matters more than URL polish
live trading: NO-GO
```

## 11. Minimal next bounded round

After this gate, the next natural host-related bounded round is:

```text
Cloud Host Durable Operator Ingress Plan V1
```

Scope:

```text
docs-only
describe what a future stable operator ingress should look like
after the first-real-request gate is actually passed
```

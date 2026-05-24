# Cloud host durable operator ingress plan V1

**Status:** ingress planning only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** describe what a future stable operator ingress should look like for the cloud host after the first-real-request gate is actually passed, without broadening access today.

This plan does not authorize domain rollout, public ingress, or live trading.
It defines the target shape for a durable operator-facing entry boundary once that later work becomes justified.

## 1. Decision

When the project is finally ready for a more durable entrypoint, the correct target is not:

```text
make everything reachable
```

The correct target is:

```text
create one stable operator ingress
keep runtime internals non-public
separate operator review surfaces from internal execution surfaces
preserve retreat and reviewability
```

This means future ingress hardening should be selective, not expansive.

## 2. What this plan is for

This plan exists to prevent a future mistake:

```text
domain gate passes,
so the host gets a nicer URL,
but no one decides which surfaces should actually be behind that URL
```

That would blur the line between:

- operator review surfaces
- internal runtime surfaces
- future broader access surfaces

The durable operator ingress should be designed as a boundary, not just a convenience.

## 3. Target ingress layers

The future stable operator ingress should have at least these conceptual layers:

### A. Operator-facing review layer

Candidate surfaces:

- `/ops`
- `/commands`
- `/commands/[id]`

Purpose:

- bounded operational review
- command classification
- evidence inspection
- retreat and operator control

This is the strongest candidate for a durable named ingress first.

### B. Internal runtime layer

Surfaces that should stay non-public:

- raw backend service ports
- worker internals
- direct runtime env / toggle handling
- direct real helper / executor-specific internals

Purpose:

- internal execution only
- never a user-facing or broad operator-facing public surface

### C. Candidate future workflow layer

Possible later surfaces:

- Trade Gate UI
- other bounded operator workflows

Purpose:

- stable operator workflow once first-real-request and review proof are already mature

These should not be automatically bundled into the first durable ingress step.

## 4. Recommended rollout order

If the domain gate is passed later, the safer rollout order would be:

1. stable operator review ingress
2. preserve internal runtime surfaces as non-public
3. verify reviewability and retreat still work under the durable ingress
4. only then consider whether bounded workflow pages should join that ingress

This keeps the first durable ingress narrow and review-centric.

## 5. What should remain outside the durable operator ingress

Even after this future ingress exists, the following should remain outside it:

- raw backend port exposure
- worker runtime internals
- direct executor helper surfaces
- direct runtime toggle mutation
- anything that could blur operator review with low-level runtime control

These should remain internal or separately controlled.

## 6. Security and review posture expectations

The future durable operator ingress should preserve all of these:

- operator identity remains explicit
- review path `/ops -> /commands -> /commands/[id]` remains canonical
- retreat posture remains immediate
- logs still support rather than replace command-detail review
- ingress changes are separate tasks, not mixed with execution proof

If a durable ingress would weaken any of these, it is the wrong ingress shape.

## 7. Relationship to domain work

This plan intentionally separates:

- “we may eventually want a hostname”

from:

- “what exact surfaces would live behind that hostname”

The hostname is secondary.
The surface boundary is primary.

That means the correct future question is not:

```text
should we add a domain?
```

but rather:

```text
which operator-facing surfaces deserve a durable stable boundary first?
```

## 8. Minimum success criteria for a future ingress task

When a future durable operator ingress task is eventually opened, it should not be considered successful unless:

- only intended operator review surfaces are brought under the stable ingress
- raw internal surfaces remain non-public
- review and retreat workflows remain intact
- the new ingress does not become a shortcut for runtime mutation
- evidence quality at `/commands/[id]` remains as strong as before

## 9. What this plan does not approve

This plan does not approve:

- domain rollout now
- broader public access now
- customer-facing ingress now
- real testnet by wider public entry now
- live trading now

It only prevents future ingress design from being improvised.

## 10. Stable status statement

At this point the correct durable-ingress summary is:

```text
future durable ingress should start with operator review surfaces
internal runtime surfaces should stay non-public
hostname decisions are secondary to surface-boundary decisions
domain remains deferred until after first-real-request proof
live trading: NO-GO
```

## 11. Minimal next bounded round

After this plan, the next natural host-related bounded round is:

```text
Cloud Host Future Public Surface Separation Rule V1
```

Scope:

```text
docs-only
define how future operator-facing stable ingress should stay separated
from any later broader workflow or customer-facing surfaces
```

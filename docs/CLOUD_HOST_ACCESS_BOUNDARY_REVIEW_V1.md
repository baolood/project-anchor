# Cloud host access boundary review V1

**Status:** boundary review only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the current access posture for the Project Anchor cloud host, identify which entry paths are still engineering-only, and state what the smallest safe access boundary should be before the first bounded real external testnet request.

This review does not approve public exposure, domain setup, or live trading. It is an access-boundary assessment.

## 1. Decision

The cloud host should currently be treated as:

```text
controlled engineering node
not stable public service entry
not customer-facing testnet endpoint
not live-trading host
```

Meaning:

- some services may be reachable for engineering/review work
- that does not imply they should be opened broadly
- access shape should stay intentionally narrow until the first real testnet request is proven under guardrails

## 2. Current boundary posture

Based on the repo and recent project state, the current boundary posture is best described as:

- backend / worker / commands chain exists and has already been exercised
- review path `/ops -> /commands -> /commands/[id]` exists conceptually and partially in UI tooling
- engineering access has relied on controlled local flows and, historically, tunnel-style access rather than a productized public entry
- real testnet execution is still guarded and not yet approved for normal outward-facing use

This is a healthy posture for the current stage. It is not yet a production ingress posture.

## 3. What is still engineering-only

The following should still be treated as engineering-only:

- direct cloud host shell access
- temporary tunnel-based access
- runtime env inspection and enablement toggles
- first bounded real testnet request execution
- review artifact creation for the first real request

These are not yet ready to be presented as stable operator or customer-facing self-service features.

## 4. What should not yet be public by default

The following should not yet be assumed safe for broad public exposure:

- raw backend service ports
- direct real-testnet execution endpoints
- runtime toggles that can switch `mock` to `real`
- internal review/evidence endpoints without tighter access posture

The reason is not that the host is broken.
The reason is that the project is still in a guarded transition from:

```text
mocked / review-complete / code-boundary-ready
```

to:

```text
first bounded real external testnet request
```

Opening too early would increase blast radius before the first real request posture is proven.

## 5. Smallest safe access posture for the next phase

Before the first bounded real testnet request, the smallest safe access posture should remain:

- narrow operator-controlled access
- clear host safety and origin allowlist
- no broad public ingress requirement
- no mandatory domain dependency
- no assumption that customers or external users should hit the host directly

In practice, that means:

- keep access intentionally constrained
- preserve easy retreat to mock or fail-closed posture
- favor reviewability over convenience

## 6. Why a domain is not yet required

A domain is not the current blocker.

The current blockers are:

- guarded real transport proof
- first real request review evidence
- access boundary discipline
- operational retreat posture

A domain would help only after those are stable enough that the host should become a durable entrypoint.

Right now a domain would mostly add:

- extra exposure surface
- extra configuration/ops responsibility
- stronger appearance of public readiness than the system has actually earned

So the current correct answer is:

```text
domain: not required yet
```

## 7. When a domain starts to make sense

A domain starts to make sense only after all of these are substantially true:

- the first bounded real testnet request has succeeded or failed in a fully reviewable way
- `/commands/[id]` and review artifacts can explain that request cleanly
- kill switch and retreat posture are operationally credible
- access boundary is no longer relying on ad hoc engineering-only patterns
- a durable external entrypoint is actually needed

Until then, domain work is secondary.

## 8. Recommended next host-related step

The most useful host-related next step is not DNS.

It is:

```text
formalize the current cloud host access classes
```

Meaning:

- what is local-only
- what is tunnel-only / operator-only
- what may later become proxied public entry
- what must stay non-public until after first real testnet proof

That decision should happen before any domain or ingress polish.

## 9. Stable status statement

At this point the correct access summary is:

```text
cloud host: usable for controlled engineering and review work
public access posture: not yet finalized
domain: not yet required
first real testnet request: still guarded
live trading: NO-GO
```

## 10. Minimal next bounded round

After this review, the next natural bounded round is:

```text
Cloud Host Access Class Matrix V1
```

Scope:

```text
docs-only
list each relevant host access path and classify it as
local-only / operator-only / future-public / forbidden-for-now
```

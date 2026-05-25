# Operator Domain Hostname Decision V1

**Status:** hostname-decision only. No DNS change, no ingress change, no runtime mutation, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Decision

The first purchased domain should not point directly at a broad product surface.

The bounded hostname decision is:

```text
choose one operator/reviewer-oriented hostname first,
and defer broader customer-facing naming until a later task
```

Recommended first hostname shape:

- `ops.<domain>`
- or `review.<domain>`

Not recommended as the first hostname:

- bare apex used as a public product homepage
- `app.<domain>` implying broad customer use
- `trade.<domain>` implying immediate execution access
- `api.<domain>` implying raw backend exposure

## 2. Why This Decision Exists

Current repository posture is:

- first-controlled-send state: `ready_for_real_review`
- domain purchase: allowed
- external showcase planning: allowed
- live trading: `NO-GO`

That means the project is ready for:

- bounded review entry planning
- operator/reviewer-oriented naming

It is not yet ready for:

- broad public positioning
- customer trading implications
- raw execution branding

## 3. Allowed First Hostname Semantics

The first hostname should communicate:

- review access
- operator control
- bounded operational visibility

Good first-label semantics:

- `ops`
- `review`
- `console-review`

These labels fit the current allowed surfaces:

- `/`
- `/ops`
- `/commands`
- `/commands/[id]`

## 4. Forbidden First Hostname Semantics

Avoid first hostnames that imply any of the following:

- public self-serve trading
- raw API access
- unrestricted execution authority
- live deployment approval
- customer onboarding completeness

Forbidden examples:

- `api.<domain>`
- `trade.<domain>`
- `live.<domain>`
- `exchange.<domain>`
- `client.<domain>`

## 5. Bare Domain Decision

The bare domain should remain undecided for now.

Reason:

- the current project posture is still review-first
- the first ingress phase should stay narrow
- the bare domain is too easy to over-interpret as a public launch surface

So the bounded rule is:

```text
buy the domain if desired,
but do not assign meaning to the apex yet
```

## 6. Pre-Hostname Gates

Before selecting the first hostname for implementation planning, all must remain true:

1. first-controlled-send status remains `ready_for_real_review`
2. actual artifact remains present
3. status integration remains `PASS`
4. live trading remains `NO-GO`
5. raw backend exposure remains forbidden
6. DNS / ingress implementation is still deferred to a separate task

## 7. STOP Conditions

Stop hostname rollout planning if:

- a proposed hostname implies public trading
- a proposed hostname implies raw API availability
- a proposed hostname implies live readiness
- the hostname cannot be explained as operator/reviewer-first
- the team starts assigning DNS meaning in the same task

## 8. Acceptance Checklist

This hostname decision is acceptable only if:

- one narrow first-hostname class is recommended
- broad/public hostname semantics are deferred
- bare domain remains undecided
- raw backend hostname semantics are blocked
- live trading implication is blocked
- DNS implementation remains out of scope

## 9. Rollback / Retreat

If hostname planning becomes too broad:

1. retreat to the operator/reviewer-only rollout plan
2. remove hostname claims that imply customer availability
3. keep DNS and ingress untouched
4. reopen hostname planning only with narrower labels

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 10. One-Line Rule

```text
The first purchased domain should adopt an operator/reviewer-oriented hostname such as ops.<domain> or review.<domain>; apex/public/app/api-style naming remains deferred, and live trading remains NO-GO.
```

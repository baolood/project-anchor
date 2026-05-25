# Operator Domain Landing Surface Decision V1

**Status:** landing-surface decision only. No DNS change, no ingress change, no frontend implementation, no runtime mutation, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Decision

The first domain-backed landing surface should be a narrow operator/reviewer entry, not a broad app shell.

Bounded decision:

```text
the first landing surface should explain the review posture,
link to /ops, /commands, and /commands/[id],
and avoid implying customer self-serve trading
```

It should function as:

- review entry
- operator guidance surface
- status and evidence orientation point

It should not function as:

- public product homepage
- broad app dashboard
- raw API directory
- trading launch page

## 2. Intended First-Landing Content

The first landing surface should contain only bounded operator/reviewer content:

1. current posture summary
   - first controlled send reviewed
   - review-first operator posture
   - live trading still `NO-GO`

2. review path summary
   - `/ops`
   - `/commands`
   - `/commands/[id]`

3. operator warnings
   - domain does not imply public release
   - domain does not imply raw backend access
   - domain does not imply live execution approval

4. bounded next-step guidance
   - where reviewers should navigate first
   - where to look for command evidence

## 3. Allowed First-Landing Links

The first landing surface may link only to:

- `/ops`
- `/commands`
- `/commands/[id]`
- one read-only checklist or guidance page already approved for operator use

These links must remain review-oriented.

## 4. Forbidden First-Landing Content

Do not put any of the following on the first domain-backed landing surface:

- “start trading”
- “connect exchange”
- “add API key”
- “deploy strategy”
- raw backend endpoint references
- worker/admin mutation controls
- runtime toggles
- live market claims
- customer onboarding language

If the first page reads like a public launch page, it is the wrong surface.

## 5. Bare Domain Behavior

The bare domain, if later connected, should initially behave the same way as the bounded operator/reviewer landing surface or remain unused.

It should not initially become:

- a marketing splash
- a customer portal
- a generic application home

This keeps domain meaning aligned with the current repository state:

- `ready_for_real_review`
- not live-approved
- not public-trading-approved

## 6. Pre-Landing Gates

Before implementing any landing surface, all must remain true:

1. `FIRST_CONTROLLED_SEND` actual artifact is still present
2. first-controlled-send status remains `ready_for_real_review`
3. status integration remains `PASS`
4. live trading remains `NO-GO`
5. raw backend exposure remains forbidden
6. DNS / ingress implementation still belongs to a separate task

## 7. STOP Conditions

Stop landing-surface planning if:

- the page starts implying customer readiness
- the page starts implying live trading
- the page cannot remain narrower than a general app shell
- the review path is no longer central
- the page would need raw backend links to feel complete

## 8. Acceptance Checklist

This landing-surface decision is acceptable only if:

- the surface is explicitly operator/reviewer-first
- the first content is review/evidence oriented
- allowed links are narrowly bounded
- public product language is absent
- live trading language is absent
- raw backend references are absent
- implementation is explicitly deferred

## 9. Rollback / Retreat

If landing-surface planning becomes too broad:

1. retreat to the hostname and rollout-plan decisions
2. remove public-product language
3. keep implementation out of scope
4. reopen only after narrowing the surface again

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 10. One-Line Rule

```text
The first domain-backed landing surface must be a narrow operator/reviewer review entry that points people toward /ops, /commands, and /commands/[id], while explicitly avoiding public-product or live-trading implications.
```

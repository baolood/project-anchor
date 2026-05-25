# Operator Domain / Ingress Rollout Plan V1

**Status:** rollout-plan only. No DNS change, no ingress change, no runtime mutation, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Current Decision

Current bounded decision:

- domain purchase: allowed / worth buying
- operator/reviewer entry planning: allowed
- live trading: `NO-GO`
- public product release: `NO-GO`

This decision comes from the current first-controlled-send status posture:

- one non-synthetic `FIRST_CONTROLLED_SEND_*.md` artifact exists
- the actual-artifact check passes
- the real-fill check passes
- the bundle check passes
- the review-pack presence check passes
- the status stack reports `ready_for_real_review`

That is enough to justify domain planning for review surfaces.
It is not enough to justify public trading release.

## 2. Intended Domain Use

The domain should be treated as:

```text
operator/reviewer entry point only
```

The intended posture is:

- review-first
- operator-oriented
- evidence-oriented
- bounded access

The domain must not be treated as:

- a public trading launch
- a customer self-serve execution surface
- a raw backend hostname
- a shortcut to live trading

## 3. Allowed Exposed Surfaces

The first allowed candidate surfaces are only:

- `/`
- `/ops`
- `/commands`
- `/commands/[id]`
- one read-only checklist or guidance page, if such a page already exists and is explicitly selected for operator review

These surfaces are acceptable only because they align with the current review flow:

```text
/ops -> /commands -> /commands/[id]
```

## 4. Forbidden Exposed Surfaces

The following must remain non-public and non-domain-exposed in this rollout phase:

- raw backend API routes
- worker controls
- runtime toggles
- secrets or env material
- mutation-heavy admin endpoints
- exchange executor helper paths
- direct database or Redis surfaces
- live trading routes
- any path that implies unrestricted execution authority

In short:

```text
domain exposure may front review surfaces
it must not front backend internals
```

## 5. Pre-Rollout Gates

Before any DNS or ingress task is allowed to start, all of the following must remain true:

1. one `FIRST_CONTROLLED_SEND_*.md` actual artifact is present
2. actual-artifact check: `PASS`
3. real-fill check: `PASS`
4. bundle check: `PASS`
5. review-pack presence check: `PASS`
6. status report remains consistent with real reviewed state
7. live trading is still explicitly `NO-GO`
8. raw backend exposure is still explicitly forbidden

If any one of these gates becomes `BLOCKED` or `FAIL`, rollout planning must stop.

## 6. DNS / Ingress Rollout Phases

The rollout must remain phased and conservative:

1. buy domain
2. do not connect DNS yet
3. choose intended hostname(s)
4. review operator-only surface scope
5. review auth posture and retreat path
6. open a separate approved task for actual DNS / ingress changes
7. only in that later task may Nginx, DNS, firewall, or routing changes be touched

This plan intentionally stops before any infrastructure mutation.

## 7. STOP Conditions

Stop immediately if any of the following becomes true:

- any first-controlled-send gate becomes `BLOCKED`
- any plan would make raw backend routes public
- any plan starts implying live trading availability
- operator-only access posture becomes unclear
- review surfaces cannot be separated from backend internals
- rollback / retreat steps are unclear
- one task starts mixing planning with DNS, ingress, firewall, or runtime edits

## 8. Acceptance Checklist

This rollout plan should be considered acceptable only if all are true:

- domain purchase is described as allowed
- domain use is restricted to operator/reviewer entry
- live trading remains `NO-GO`
- public product release remains `NO-GO`
- allowed surfaces are narrowly bounded
- raw backend exposure is explicitly forbidden
- DNS / ingress implementation is explicitly deferred to a separate task
- stop conditions are explicit
- rollback / retreat is explicit

## 9. Rollback / Retreat Plan

If the domain planning posture becomes confused or over-broad:

1. stop all domain rollout discussion
2. revert to the current operator-only review posture
3. do not connect DNS
4. do not change ingress
5. do not expose raw backend surfaces
6. reopen a narrower planning task only after the boundary is rewritten clearly

For this document itself, rollback is docs-only:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 10. One-Line Rule

```text
The domain may be purchased now, but it may only be planned as an operator/reviewer review entry point; any DNS, ingress, or broader exposure change must wait for a separate approved rollout task, and live trading remains NO-GO.
```

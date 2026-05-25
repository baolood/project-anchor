# Operator Domain Auth Boundary Decision V1

**Status:** auth-boundary decision only. No auth implementation, no DNS change, no ingress change, no runtime mutation, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Decision

The first domain-backed operator/reviewer entry must not be publicly readable by default.

Bounded decision:

```text
the first domain-backed review entry requires an explicit operator/reviewer access boundary
and must not be treated as an open public surface
```

This round does not choose a final auth product or vendor.
It only fixes the boundary requirement.

## 2. Why This Decision Exists

Current repository posture is:

- first-controlled-send state: `ready_for_real_review`
- domain purchase: allowed
- operator/reviewer review entry planning: allowed
- live trading: `NO-GO`

That posture is strong enough for bounded review access planning.
It is not strong enough for unrestricted public ingress.

Even though the domain may front review surfaces such as:

- `/ops`
- `/commands`
- `/commands/[id]`

those surfaces still expose operational context and evidence flow.
They must therefore remain access-bounded.

## 3. Required Boundary

The first domain-backed review entry must satisfy all of the following:

- only intended operators/reviewers may enter
- broad public discovery should not imply usable access
- raw backend should remain unreachable from the same boundary
- worker/runtime controls remain unavailable
- live trading implications remain absent

In short:

```text
review surface can be domain-backed
review surface cannot be anonymous-by-default
```

## 4. Acceptable First-Phase Auth Posture

The first-phase auth posture should be one of these bounded classes:

- explicit allowlisted operator/reviewer access
- temporary review-only auth gate
- tightly scoped team-only access boundary

This decision intentionally does not select:

- a final identity provider
- a final SSO product
- a final login implementation

Those are later implementation tasks.

## 5. Forbidden First-Phase Auth Posture

Do not allow any of the following as the first boundary:

- anonymous public access
- “security by obscurity” only
- open access because “it is just review”
- broad internet access with no operator distinction
- customer-facing login semantics
- any auth posture that indirectly exposes raw backend surfaces

## 6. Relation To Landing Surface

The landing surface may remain narrow and review-oriented, but that alone is not enough.

Both must be true:

1. the surface is operator/reviewer-first
2. the access boundary is operator/reviewer-bounded

If only the first is true, the boundary is still incomplete.

## 7. Pre-Auth-Boundary Gates

Before planning any concrete auth implementation, all must remain true:

1. first-controlled-send status remains `ready_for_real_review`
2. domain purchase remains bounded to operator/reviewer use
3. hostname decision remains narrow (`ops.<domain>` / `review.<domain>` style)
4. landing surface remains review-oriented
5. live trading remains `NO-GO`
6. DNS / ingress implementation remains a separate task

## 8. STOP Conditions

Stop immediately if:

- the auth discussion turns into public-product access planning
- the plan starts implying customer accounts
- raw backend access becomes coupled to the same auth boundary
- the review entry cannot be separated from future product login
- rollout pressure starts skipping the access-boundary question

## 9. Acceptance Checklist

This auth-boundary decision is acceptable only if:

- the first domain-backed surface is explicitly non-public by default
- operator/reviewer-only access is required
- raw backend remains blocked
- live trading remains `NO-GO`
- implementation details remain deferred
- DNS / ingress changes remain out of scope

## 10. Rollback / Retreat

If auth-boundary planning becomes too broad:

1. retreat to the landing-surface and hostname decisions
2. remove customer/public access language
3. keep implementation out of scope
4. reopen only with operator/reviewer boundary language

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 11. One-Line Rule

```text
The first domain-backed operator/reviewer entry may be planned now, but it must sit behind an explicit operator/reviewer access boundary and must not be treated as an anonymous public surface.
```

# Operator Domain Ingress Task Opening Rule V1

**Status:** task-opening rule only. No DNS change, no ingress change, no runtime mutation, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Purpose

This rule answers one narrow question:

```text
when is the project allowed to open a separate implementation task
for operator-domain DNS / ingress rollout?
```

This rule does not implement anything itself.
It only decides when a later infrastructure task may legitimately begin.

## 2. Current Planning Boundary

The project already has:

- operator domain rollout plan
- hostname decision
- landing-surface decision
- auth-boundary decision
- DNS deferral rule
- ingress prerequisite checklist

That means the planning stack is now sufficient to decide whether a later task may be opened.

It does **not** mean DNS or ingress is already approved.

## 3. Opening Rule

A separate DNS / ingress implementation task may be opened only if all of these remain true:

1. first-controlled-send status remains `ready_for_real_review`
2. the actual artifact remains present and accepted
3. first-controlled-send status integration remains `PASS`
4. the operator-domain rollout plan still defines operator/reviewer-only posture
5. hostname decision remains narrow
6. landing-surface decision remains review-first
7. auth-boundary decision remains explicit and non-public by default
8. raw backend exposure remains forbidden
9. live trading remains explicitly `NO-GO`
10. rollback / retreat expectations are clear enough to describe in the future infrastructure task

If any one of these falls out of alignment, the implementation task must not be opened.

## 4. What “Task May Be Opened” Means

Opening the task means only:

- a separate task may now be defined
- that task may scope DNS / ingress implementation work
- that task may present concrete implementation options

It does **not** mean:

- DNS should be changed immediately
- ingress should be exposed immediately
- the system is public
- live trading is approved

## 5. What The Future Implementation Task Must Still Respect

Even after this opening rule is satisfied, the later implementation task must still preserve:

- operator/reviewer-only posture
- bounded landing surface
- no raw backend exposure
- no worker/runtime toggle exposure
- no secret exposure
- no live-trading implication

In short:

```text
this rule may open the door to a later infrastructure task,
but it does not weaken any existing safety boundary
```

## 6. STOP Conditions

Do not open the implementation task if:

- someone treats “worth buying” as “ready for public ingress”
- the hostname or landing surface starts implying product launch
- auth boundary is still conceptual but not bounded enough to describe
- rollback expectations cannot be written cleanly
- the future task would mix too many concerns at once

## 7. Acceptance Checklist

This opening rule is acceptable only if:

- it clearly distinguishes planning from implementation
- it requires the prerequisite checklist to stay clean
- it preserves operator/reviewer-only posture
- it preserves live-trading `NO-GO`
- it preserves raw-backend blocking
- it requires a separate future task for actual DNS / ingress work

## 8. Rollback / Retreat

If the opening rule starts being interpreted as deployment approval:

1. stop the discussion
2. retreat to the DNS deferral rule and prerequisite checklist
3. refuse to open the infrastructure task
4. reopen only after the boundary is narrowed again

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 9. One-Line Rule

```text
The project may open a separate operator-domain DNS / ingress implementation task only after every planning-layer boundary remains cleanly true; opening that task is not the same as approving public exposure or live trading.
```

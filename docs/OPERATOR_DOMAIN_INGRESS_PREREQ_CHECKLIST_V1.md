# Operator Domain Ingress Prereq Checklist V1

**Status:** prerequisite checklist only. No DNS change, no ingress change, no runtime mutation, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Purpose

This checklist exists for one narrow question:

```text
is the project actually ready to open a separate DNS / ingress implementation task
for the operator/reviewer domain entry?
```

This checklist does not authorize implementation by itself.
It only determines whether a later rollout task may begin.

## 2. Current Boundary

Current repository posture remains:

- domain purchase: allowed
- operator/reviewer hostname planning: allowed
- landing-surface planning: allowed
- auth-boundary planning: allowed
- DNS / ingress implementation: still deferred
- live trading: `NO-GO`

## 3. Required Pre-Implementation Checks

All of the following should be true before a dedicated ingress task is opened:

1. first-controlled-send status remains `ready_for_real_review`
2. one `FIRST_CONTROLLED_SEND_*.md` actual artifact remains present
3. first-controlled-send status integration still passes
4. operator/reviewer rollout plan remains the active posture
5. hostname decision remains narrow (`ops.<domain>` / `review.<domain>` class)
6. landing surface remains review-oriented
7. auth boundary remains explicitly non-public by default
8. raw backend exposure remains forbidden
9. live trading remains explicitly `NO-GO`
10. rollback / retreat expectations are still understandable

## 4. Required Non-Goals

A future ingress task must still preserve these non-goals:

- no public customer trading implication
- no raw backend publication
- no worker or runtime toggle exposure
- no secret exposure
- no live-trading implication

If the future task would weaken any of these, it is not ready to begin.

## 5. STOP Conditions

Do not open an ingress implementation task if any of the following is true:

- first-controlled-send status falls below `ready_for_real_review`
- actual artifact becomes missing or disputed
- rollout planning starts implying product launch
- hostname meaning becomes too broad
- landing surface no longer stays review-first
- auth boundary is unclear
- rollback path is unclear

## 6. Checklist

Mark each item explicitly:

- `ready_for_real_review` still true: yes/no
- actual first-controlled-send artifact still present: yes/no
- status integration still `PASS`: yes/no
- operator/reviewer rollout plan still current: yes/no
- hostname decision still narrow: yes/no
- landing-surface decision still narrow: yes/no
- auth-boundary decision still non-public by default: yes/no
- raw backend exposure still blocked: yes/no
- live trading still `NO-GO`: yes/no
- future rollback / retreat path still clear: yes/no

If any answer is not a clean `yes`, ingress implementation should remain deferred.

## 7. Interpretation

Interpret the checklist this way:

- all `yes`: the project may open a separate ingress implementation task
- any `no`: the project should remain in planning-only posture

Passing this checklist does **not** mean:

- DNS should be changed immediately
- ingress is automatically approved
- the product is public
- live trading is ready

It means only:

```text
the project may now justify opening a separate reviewed infrastructure task
```

## 8. Rollback / Retreat

If checklist use starts being confused with rollout approval:

1. stop the discussion
2. retreat to the DNS deferral rule
3. keep implementation out of scope
4. reopen only when the checklist is used as a gate, not as deployment approval

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 9. One-Line Rule

```text
The project may consider opening a separate ingress implementation task only after every operator-domain prerequisite stays cleanly true; otherwise DNS and ingress remain deferred.
```

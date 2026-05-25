# Real Credential Handoff Task Opening Rule V1

**Status:** task-opening rule only. No credential injection, no runtime mutation, no external request, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Purpose

This rule answers one narrow question:

```text
when is the project allowed to open a separate implementation task
for real canonical TESTNET credential handoff?
```

This rule does not perform the handoff.
It only decides when that next task may begin.

## 2. Current Planning Boundary

The project already has:

- canonical cloud-host mock posture
- reviewed canonical mock evidence
- one non-synthetic first-controlled-send artifact
- a real credential handoff decision
- a real credential handoff prerequisite checklist

That means the planning layer is now strong enough to determine whether a later task may be opened.

It does **not** mean credentials are approved for injection now.

## 3. Opening Rule

A separate real credential handoff implementation task may be opened only if all of these remain true:

1. first-controlled-send status remains `ready_for_real_review`
2. actual first-controlled-send artifact remains present and accepted
3. first-controlled-send status integration remains `PASS`
4. canonical runtime env alignment remains `PASS`
5. cloud-host canonical mock smoke evidence remains reviewable
6. `TESTNET_EXECUTOR_MODE` remains `mock`
7. `TESTNET_EXECUTOR_REAL_ENABLE` remains `0`
8. canonical runtime remains credential-absent
9. live trading remains explicitly `NO-GO`
10. rollback / retreat expectations can be written concretely in the later task

If any one of these falls out of alignment, the implementation task must not be opened.

## 4. What “Task May Be Opened” Means

Opening the task means only:

- a separate reviewed task may now be defined
- that task may scope credential handoff mechanics
- that task may describe bounded verification and rollback steps

It does **not** mean:

- credentials should be injected immediately
- `TESTNET_EXECUTOR_MODE` should be switched immediately
- `TESTNET_EXECUTOR_REAL_ENABLE` should be set immediately
- a real external request is already approved
- live trading is approved

## 5. What The Future Implementation Task Must Still Respect

Even after this opening rule is satisfied, the later implementation task must still preserve:

- bounded credential handling
- review-safe presence checks only
- no secret disclosure
- no automatic switch to `real`
- no hidden external request
- no live-trading implication

In short:

```text
this rule may open the door to a later credential handoff task,
but it does not weaken any existing safety boundary
```

## 6. STOP Conditions

Do not open the implementation task if:

- mock posture is already drifting
- credential discussion is being used to imply real-send approval
- rollback expectations cannot be stated clearly
- the future task would mix credentials, ingress, and live-trading decisions in one step
- the current evidence chain can no longer be explained cleanly through review artifacts and `/commands/[id]`

## 7. Acceptance Checklist

This opening rule is acceptable only if:

- it clearly distinguishes planning from execution
- it requires the prerequisite checklist to stay clean
- it preserves credential-free mock posture in the current round
- it preserves live-trading `NO-GO`
- it requires a separate future task for actual handoff work

## 8. Rollback / Retreat

If this opening rule starts being interpreted as credential approval:

1. stop the discussion
2. retreat to the handoff decision and prerequisite checklist
3. refuse to open the implementation task
4. reopen only after the boundary is narrowed again

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 9. One-Line Rule

```text
The project may open a separate real credential handoff implementation task only after every mock-posture prerequisite remains cleanly true; opening that task is not the same as approving credential injection, real mode, or external requests.
```

# Real Credential Handoff Prereq Checklist V1

**Status:** prerequisite checklist only. No credential injection, no runtime mutation, no external request, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Purpose

This checklist exists for one narrow question:

```text
is the project actually ready to open a separate real-credential handoff task?
```

This checklist does not authorize credential injection by itself.
It only determines whether a later bounded handoff task may begin.

## 2. Current Boundary

Current repository posture remains:

- cloud host on latest mainline
- canonical `TESTNET_*` runtime posture aligned
- `TESTNET_EXECUTOR_MODE=mock`
- `TESTNET_EXECUTOR_REAL_ENABLE=0`
- canonical cloud-host mock smoke reviewed
- one non-synthetic `FIRST_CONTROLLED_SEND_*.md` artifact present
- first-controlled-send status: `ready_for_real_review`
- live trading: `NO-GO`

## 3. Required Pre-Handoff Checks

All of the following should be true before a dedicated real-credential handoff task is opened:

1. first-controlled-send status remains `ready_for_real_review`
2. actual first-controlled-send artifact remains present and accepted
3. status integration remains `PASS`
4. canonical runtime env alignment remains `PASS`
5. canonical cloud-host mock smoke evidence remains reviewable
6. `TESTNET_EXECUTOR_MODE` remains `mock`
7. `TESTNET_EXECUTOR_REAL_ENABLE` remains `0`
8. no canonical `TESTNET_*` credential values are already present in runtime
9. live trading remains explicitly `NO-GO`
10. rollback / retreat expectations can be described cleanly for a future handoff task

## 4. Required Non-Goals

A future handoff task must still preserve these non-goals:

- no immediate real external request
- no hidden credential persistence
- no silent switch to `real`
- no live-trading implication
- no weakening of review evidence requirements

If the future task would weaken any of these, it is not ready to begin.

## 5. STOP Conditions

Do not open a real-credential handoff task if any of the following is true:

- first-controlled-send status falls below `ready_for_real_review`
- runtime env alignment regresses
- mock-smoke evidence becomes disputed
- `TESTNET_EXECUTOR_MODE` has already drifted away from `mock`
- `TESTNET_EXECUTOR_REAL_ENABLE` has already drifted away from `0`
- rollback expectations are unclear
- credential handling discussion starts getting mixed with live-trading approval

## 6. Checklist

Mark each item explicitly:

- `ready_for_real_review` still true: yes/no
- actual first-controlled-send artifact still present: yes/no
- status integration still `PASS`: yes/no
- canonical runtime env alignment still `PASS`: yes/no
- mock-smoke evidence still reviewable: yes/no
- `TESTNET_EXECUTOR_MODE=mock` still true: yes/no
- `TESTNET_EXECUTOR_REAL_ENABLE=0` still true: yes/no
- canonical runtime still credential-absent: yes/no
- live trading still `NO-GO`: yes/no
- future rollback / retreat path still clear: yes/no

If any answer is not a clean `yes`, real-credential handoff should remain deferred.

## 7. Interpretation

Interpret the checklist this way:

- all `yes`: the project may open a separate bounded real-credential handoff task
- any `no`: the project should remain in canonical mock posture

Passing this checklist does **not** mean:

- credentials should be injected immediately
- real mode should be enabled immediately
- real external request is approved
- live trading is ready

It means only:

```text
the project may now justify opening a separate reviewed credential handoff task
```

## 8. Rollback / Retreat

If checklist use starts being confused with credential approval:

1. stop the discussion
2. retreat to the handoff decision
3. keep implementation out of scope
4. reopen only when the checklist is used as a gate, not as execution approval

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 9. One-Line Rule

```text
The project may consider opening a separate real-credential handoff task only after every mock-posture prerequisite stays cleanly true; otherwise canonical TESTNET runtime must remain credential-free and mock-only.
```

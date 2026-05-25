# Real Credential Handoff Decision V1

**Status:** decision only. No credential injection, no runtime mutation, no external request, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Purpose

This decision answers one narrow question:

```text
when is the project allowed to move from canonical TESTNET mock posture
to a real credential handoff discussion?
```

This round does not inject credentials.
It only decides when that next category of work may begin.

## 2. Current State

Current bounded state is:

- cloud host is on the latest mainline
- backend and worker are healthy
- canonical `TESTNET_*` runtime posture is aligned
- `TESTNET_EXECUTOR_MODE=mock`
- `TESTNET_EXECUTOR_REAL_ENABLE=0`
- canonical cloud-host mock smoke has been run
- one non-synthetic `FIRST_CONTROLLED_SEND_*.md` artifact exists
- first-controlled-send status is `ready_for_real_review`

At the same time:

- canonical testnet credentials are still absent
- real external request evidence does not yet exist
- live trading remains `NO-GO`

## 3. Decision

The project may now discuss a bounded real credential handoff task,
but it may not inject credentials yet as part of this decision.

In short:

```text
real credential handoff discussion is now allowed
real credential handoff execution is still deferred
```

## 4. Why This Boundary Exists

The mock posture has already proven:

- canonical `ORDER + execution_mode=testnet` path exists
- policy and kill-switch review occur in order
- credential absence fails closed before external request
- review evidence is strong enough to classify the event

That is enough to justify planning the next category.

It is not enough to justify silently moving credentials into runtime without its own bounded approval.

## 5. What A Future Handoff Task Must Cover

The future credential handoff task, if opened later, must cover all of these explicitly:

1. credential source of truth
2. who injects the credentials
3. where credentials may exist temporarily
4. how presence is verified without disclosing values
5. how `TESTNET_EXECUTOR_REAL_ENABLE` stays off until separately approved
6. how rollback removes or disables the real-credential posture

## 6. What This Decision Does Not Approve

This decision does not approve:

- setting `TESTNET_EXCHANGE_API_KEY`
- setting `TESTNET_EXCHANGE_API_SECRET`
- setting `TESTNET_EXCHANGE_KEY_ID`
- changing `TESTNET_EXECUTOR_MODE` to `real`
- changing `TESTNET_EXECUTOR_REAL_ENABLE` to `1`
- performing a real external testnet request

## 7. Preconditions For Opening A Future Handoff Task

Before a separate credential handoff task may be opened, all of these should remain true:

1. first-controlled-send status remains `ready_for_real_review`
2. canonical runtime env alignment remains `PASS`
3. mock-smoke evidence remains reviewable
4. operator/reviewer posture remains bounded
5. live trading remains `NO-GO`
6. rollback expectations can be written clearly

## 8. STOP Conditions

Do not open a future credential handoff task if:

- current canonical runtime alignment regresses
- mock-smoke evidence becomes disputed
- a reviewer cannot explain `/commands/[id]` evidence cleanly
- credential handling starts getting mixed with live-trading approval
- rollback / credential removal posture is unclear

## 9. Acceptance Checklist

This decision is acceptable only if:

- it clearly allows discussion of a future handoff task
- it clearly forbids credential injection in this round
- it clearly forbids moving to `real` mode in this round
- it keeps live trading `NO-GO`
- it preserves rollback and review requirements

## 10. Rollback / Retreat

If this decision starts being interpreted as permission to inject credentials immediately:

1. stop the discussion
2. retreat to canonical mock posture
3. require a separate bounded handoff task
4. keep `TESTNET_EXECUTOR_MODE=mock`
5. keep `TESTNET_EXECUTOR_REAL_ENABLE=0`

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 11. One-Line Rule

```text
The project may now open a separate real-credential handoff discussion, but no canonical TESTNET credentials may enter runtime and no real executor mode may be enabled until that later task is explicitly approved.
```

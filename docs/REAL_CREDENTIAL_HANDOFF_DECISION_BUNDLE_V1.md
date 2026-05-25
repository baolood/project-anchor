# Real Credential Handoff Decision Bundle V1

**Status:** bundle index only. No credential injection, no runtime mutation, no external request, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Purpose

This bundle exists to answer one narrow need:

```text
when the project is ready to discuss a separate real credential handoff task,
where should a reviewer start reading?
```

The answer is now:

```text
start here, then read the bounded real-credential planning stack in order
```

## 2. Current Status

At this point the repository has:

- canonical cloud-host mock posture aligned
- canonical cloud-host mock smoke evidence
- one real first-controlled-send review artifact
- first-controlled-send status: `ready_for_real_review`
- real credential handoff discussion allowed
- real credential handoff execution still deferred
- live trading still `NO-GO`

That means the planning stack is mature enough to be bundled.

## 3. Reading Order

Review the real-credential planning stack in this order:

1. [REAL_CREDENTIAL_HANDOFF_DECISION_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_CREDENTIAL_HANDOFF_DECISION_V1.md)
2. [REAL_CREDENTIAL_HANDOFF_PREREQ_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_CREDENTIAL_HANDOFF_PREREQ_CHECKLIST_V1.md)
3. [REAL_CREDENTIAL_HANDOFF_TASK_OPENING_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_CREDENTIAL_HANDOFF_TASK_OPENING_RULE_V1.md)

## 4. What This Bundle Confirms

Taken together, the bundle confirms:

- the project may now discuss a later handoff task
- current canonical runtime must remain credential-free
- current canonical runtime must remain mock-only
- real executor mode is still deferred
- live trading remains `NO-GO`
- any actual handoff work still needs a separate implementation task

## 5. What This Bundle Does Not Approve

This bundle does not approve:

- injecting `TESTNET_EXCHANGE_API_KEY`
- injecting `TESTNET_EXCHANGE_API_SECRET`
- injecting `TESTNET_EXCHANGE_KEY_ID`
- switching `TESTNET_EXECUTOR_MODE` to `real`
- switching `TESTNET_EXECUTOR_REAL_ENABLE` to `1`
- performing a real external request
- approving live trading

If a reviewer needs any of those, a later separate task must still be opened.

## 6. Expected Use

This bundle should be used in only two cases:

1. deciding whether the real-credential planning layer is complete enough
2. deciding whether a separate real-credential handoff implementation task may be opened

It should not be used as:

- implicit credential approval
- implicit real-mode approval
- implicit external-request approval
- implicit live-trading approval

## 7. Rollback / Retreat

If the bundle starts being used as if it were handoff approval:

1. stop
2. retreat to the handoff decision and prerequisite checklist
3. require a separate implementation task

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 8. One-Line Rule

```text
This bundle is the bounded review starting point for any future real-credential handoff discussion, but it does not itself authorize credential injection, real executor mode, external requests, or live trading.
```

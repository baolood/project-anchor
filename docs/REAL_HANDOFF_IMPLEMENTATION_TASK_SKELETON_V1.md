# Real Handoff Implementation Task Skeleton V1

**Status:** implementation-task skeleton only. No credential injection, no runtime mutation, no external request, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Purpose

This file defines the smallest acceptable skeleton for a future real credential handoff implementation task.

It does **not** execute the handoff.
It only fixes what that future task must declare before any implementation work starts.

## 2. Task Class

This is not another planning closeout.

It is the minimum task skeleton for a later bounded implementation round whose purpose would be:

```text
prepare a real credential handoff path for canonical TESTNET runtime
without yet approving real external requests or live trading
```

## 3. Required Task Header

A future implementation task should explicitly declare:

- `Repo`
- `Branch`
- `Task name`
- `Goal`
- `Allowed files`
- `Forbidden files`
- `Required changes`
- `Validation commands`
- `Acceptance`
- `Commit message`
- `Closeout required`

If any one of these is missing, the task is incomplete.

## 4. Required Allowed-File Scope

The future handoff implementation task must keep file scope narrow.

Allowed files should be limited to only the exact runtime / review surfaces being changed for that round, for example:

- one bounded backend runtime file
- one bounded cloud-host runtime note
- one bounded test file

The task must not begin with a broad “any backend file” allowance.

## 5. Required Forbidden Scope

The future handoff implementation task must explicitly forbid at least:

- `anchor-backend/migrations/**`
- `anchor-console/**`
- `.env`
- deploy config
- docker / compose files
- nginx / firewall / DNS config
- live trading paths
- any file not needed for the bounded handoff slice

Unless a later task is explicitly about one of those areas, they remain forbidden.

## 6. Minimum Implementation Goal

The first real handoff implementation task should target only one bounded objective:

```text
prove the project can prepare canonical TESTNET credential presence handling
without disclosing values, without enabling real mode by accident,
and without issuing an external request
```

That means the first implementation task should still preserve:

- `TESTNET_EXECUTOR_MODE=mock`
- `TESTNET_EXECUTOR_REAL_ENABLE=0`
- no external request
- no live-trading implication

## 7. Required Non-Goals

The first implementation task must explicitly state these non-goals:

- no real API key injection into committed files
- no direct editing of `.env`
- no `docker compose` / deploy mutation
- no switch to `real`
- no external request
- no live trading

If the task cannot keep those non-goals explicit, it is too broad.

## 8. Required Validation Commands

The future implementation task must provide a short validation set, for example:

- `git diff --check`
- a narrow script or test for the changed path
- `./scripts/check_local_box_baseline.sh`
- `./scripts/check_go_live_rules.sh`
- `git status --short`

The validation section must remain short and task-specific.

## 9. Required Rollback Shape

The future implementation task must declare rollback before work starts.

At minimum it should specify:

- how to revert the commit
- how to retreat to canonical mock posture
- how to verify that runtime is still not in `real`

If rollback is unclear, the task should not begin.

## 10. Acceptance Conditions

A future real handoff implementation task is acceptable only if all are true:

- file scope is narrow
- forbidden scope is explicit
- implementation goal is bounded
- no credential values are disclosed
- no runtime mutation occurs outside the declared slice
- no real executor mode is enabled
- no external request is attempted
- rollback is explicit

## 11. One-Line Rule

```text
The first real handoff implementation task must be a narrow runtime-preparation slice only: no real credentials in repo files, no real mode, no external request, no deploy mutation, and explicit rollback from the start.
```

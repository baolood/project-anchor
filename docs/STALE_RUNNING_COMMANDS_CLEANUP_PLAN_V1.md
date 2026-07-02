# Stale Running Commands Cleanup Plan V1

## 1. Purpose

- prepare a minimal cleanup plan for the two stale `RUNNING` commands that blocked canary preflight
- no database mutation in this task
- no canary retry
- no real external exchange request

This plan defines what a future separately authorized cleanup may do. It does not execute cleanup.

## 2. Source Review

- source review: `docs/STALE_RUNNING_COMMANDS_READONLY_REVIEW_V1.md`
- both commands are RUNNING: YES
- last event for both: `POLICY_ALLOW`
- MARK_DONE present: NO
- MARK_FAILED present: NO
- external request event present: NO
- external_order_id present: NO
- recommendation: `SAFE_TO_MARK_FAILED_WITH_STALE_RUNNING_REASON`

Target command IDs:

- `order-fec6a82f-b8fe-4f4c-ae45-972aaf26e91e`
- `order-e66c32df-4c14-4dd0-b23e-dce6a8835740`

## 3. Proposed Cleanup

A future cleanup task may do only the following, after explicit operator authorization:

- mark only the two target command IDs as `FAILED`
- failure reason: `stale_running_pre_canary_cleanup`
- cleanup reason: canary preflight blocker, stale locked RUNNING commands, no external request evidence
- preserve all existing rows
- preserve all existing events
- do not delete anything
- do not unlock without marking failure
- do not create an external request
- do not retry the original orders
- do not execute canary

## 4. Required Pre-Cleanup Guard

The future cleanup task must verify before mutation:

- workspace clean
- local branch is `main`
- local main synced with origin
- current HEAD confirmed
- DB target rows still `RUNNING`
- target IDs match exactly
- target command count is exactly 2
- no external request event appears before cleanup
- no external_order_id appears before cleanup
- no MARK_DONE appears before cleanup
- no MARK_FAILED appears before cleanup
- worker heartbeat checked
- kill switch checked
- canary execution in cleanup task: NO
- real external exchange request in cleanup task: NO

## 5. Expected Post-Cleanup Evidence

After the future cleanup, the closeout must record:

- both target commands status: FAILED
- failure reason recorded as `stale_running_pre_canary_cleanup`
- MARK_FAILED or equivalent failure evidence present if the system uses events for manual cleanup
- external request event remains absent
- external_order_id remains absent
- canary request sent: NO
- real external exchange request sent: NO
- live trading: NO-GO
- go-live: NO-GO

## 6. Rollback / Anomaly Handling

- Prefer no rollback unless the cleanup mutation itself is wrong.
- If wrong target IDs were modified, stop and document anomaly.
- If only this documentation is wrong, revert the documentation commit.
- Do not retry canary automatically after cleanup.
- Do not retry either stale command.
- Do not create a second cleanup mutation without new authorization.

## 7. Current Task Boundary

- DB mutation performed: NO
- commands marked FAILED: NO
- commands unlocked: NO
- commands deleted: NO
- worker restarted: NO
- canary retried: NO
- real external exchange request sent: NO
- live trading: NO-GO
- go-live: NO-GO

## 8. Next Safe Status

- `READY_FOR_STALE_RUNNING_COMMANDS_CLEANUP_PLAN_PR_MERGE`

After this plan is merged and baseline is clean, the next possible status is `READY_FOR_STALE_RUNNING_COMMANDS_CLEANUP_AUTHORIZATION`.

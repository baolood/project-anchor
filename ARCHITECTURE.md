# Architecture: Command → Action → Pipeline → Policy

This document describes the integrated data flow and key semantics for domain commands (NOOP / FAIL / FLAKY), retry, and events.

## Data flow

```
Command (PENDING)
  → Runner (pick one)
  → PICKED event
  → Policies (idempotency / rate limit / cooldown)
  → [POLICY_BLOCK → mark_failed, MARK_FAILED, done]
  → [POLICY_ALLOW] → Action Pipeline (validate → execute → postprocess)
  → ACTION_OK / ACTION_FAIL
  → mark_done / mark_failed
  → MARK_DONE / MARK_FAILED
  → Events → Console (Load events)
```

- **Endpoints**: `POST /domain-commands/noop|fail|flaky`, `POST /domain-commands/{id}/retry`, `GET /domain-commands/{id}/events`. No change to URLs or response shapes.
- **Worker** picks one PENDING command (with lock), increments **attempt** once per pick, then runs policies and action pipeline. **Retry** only resets status to PENDING; it does **not** increment attempt. Attempt increases only when the worker picks the command again.

## Key semantics

- **Attempt**: Incremented only in the worker when a command is picked (`attempt = attempt + 1` in the pick UPDATE). The retry endpoint does not change attempt; it only sets `status = 'PENDING'` and clears error/result/lock. So: first run attempt=1 (e.g. FAILED), after retry still attempt=1 until worker picks again (then attempt=2, then DONE).
- **Idempotency**: Per `(command_id, attempt)`. If `domain_events` already has MARK_DONE or MARK_FAILED for that command_id and attempt, the policy blocks to avoid writing a terminal state twice for the same attempt. Retry uses a new pick, so a new attempt number; idempotency does not block the retry flow.
- **Policy block**: When any policy returns `allowed=False`, the runner writes POLICY_BLOCK, calls `mark_failed`, then writes MARK_FAILED (so the command has a terminal state and the event log is consistent). We do not leave the command PENDING without a terminal event to keep auditing and UI state clear.

## Event types (unchanged)

Required for existing e2e: **PICKED**, **ACTION_FAIL**, **MARK_FAILED**, **RETRY**, **ACTION_OK**, **MARK_DONE**. Additional: POLICY_BLOCK, POLICY_ALLOW, EXCEPTION. All event payloads that are used for policy or auditing include `type` and `attempt` where applicable (e.g. ACTION_FAIL, MARK_FAILED, RETRY, POLICY_BLOCK).

## How to verify

From the project root (e.g. `/Users/baolood/Projects/project-anchor`):

1. **Full restart + retry + events** (includes backend/worker rebuild, migration, Next dev, retry e2e, events e2e):
   ```bash
   ./scripts/run_fix_restart_verify.sh
   ```
   Expect: `PASS_OR_FAIL=PASS` at the end.

2. **Retry + events only** (assumes backend/worker and Next already running):
   ```bash
   ./scripts/run_full_retry_with_events.sh
   ```
   Expect: `RETRY_E2E_PASS=YES`, `EVENTS_E2E_PASS=YES`, `PASS_OR_FAIL=PASS`.

3. **One-shot verification** (orchestrates the above and optional closure):
   ```bash
   ./scripts/verify_all_e2e.sh
   ```
   Expect: final template with `PASS_OR_FAIL=PASS`, `RETRY_E2E_PASS=YES`, `EVENTS_E2E_PASS=YES`; retry checklist has `ATTEMPT_AT_FAIL=1`, `ATTEMPT_AT_DONE=2`; events checklist has all `HAS_*` YES.

Retry checklist output is written to `/tmp/checklist_retry_e2e_last.out`; events checklist to `/tmp/checklist_events_e2e_last.out` (or as set by the scripts).

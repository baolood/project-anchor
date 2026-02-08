# ADR-0002: Command State Machine and Ownership Rules

## Status
Accepted

## Context
Project Anchor uses Commands to coordinate work across the console UI, backend API, and workers.
To avoid race conditions, double-processing, and "random" state changes, we must define strict
state transitions and ownership rules.

## Decision
We define the Command lifecycle as a strict, one-way state machine:

PENDING -> PROCESSING -> DONE
                    \-> FAILED

### Ownership rules
- Console UI:
  - May create a Command (POST).
  - Must treat Command status as read-only. No state transitions.
- Backend API:
  - Owns validation, persistence, and state transition authorization.
  - Exposes Commands to UI and workers via stable contracts.
- Worker:
  - May transition a Command only when it has acquired the lock.

### Allowed transitions (only)
- PENDING -> PROCESSING
- PROCESSING -> DONE
- PROCESSING -> FAILED

### Locking rules
- Entering PROCESSING requires setting:
  - locked_by (worker id)
  - locked_at (ISO8601)
- A worker must not process a command it did not lock.

### Failure rules
- FAILED is terminal.
- When status == FAILED, error must be set (non-empty string).

### Result rules
- DONE is terminal.
- When status == DONE, result may be set (object) and error must be null.

### Retry policy (minimal contract-level rule)
- Retries are represented by incrementing attempt.
- Retry is only possible by creating a new Command (preferred) or by an explicit, future "reset"
  mechanism (not part of this ADR).

## Consequences
- Prevents concurrent workers from processing the same command.
- Keeps UI simple and avoids "smart UI" bugs.
- Forces all state changes through a single authority, reducing debugging time and regressions.

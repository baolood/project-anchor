# ADR-0003: Atomic Claiming of PENDING Commands

## Status
Accepted

## Context
Multiple workers may run concurrently. If claiming a command is not atomic,
the same PENDING command can be processed more than once, causing inconsistent
state, duplicate side effects, and hard-to-debug races.

## Decision
Workers must claim commands using an **atomic** operation that:
- selects a single PENDING command, and
- transitions it to PROCESSING in the same transactional boundary, and
- sets the lock fields (locked_by, locked_at) at the time of claiming.

Claiming is allowed only for status == PENDING.

### Recommended pattern (Postgres)
Use row-level locking with `FOR UPDATE SKIP LOCKED` (or an equivalent mechanism)
to ensure concurrent workers do not claim the same row.

### Claim invariants
- After a successful claim:
  - status == PROCESSING
  - locked_by is set to the claiming worker id
  - locked_at is set to current time
  - attempt is incremented
- A worker must not execute a command it did not lock.

## Consequences
- Prevents double-processing under concurrency.
- Makes worker behavior deterministic and auditable.
- Simplifies recovery: no rollback to PENDING; retries use a new command or a
  future explicit reset mechanism.

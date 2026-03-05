# VERIFY Phase 3.11 — Idempotency → ops_audit

## Goal
When POST /commands uses X-Idempotency-Key, idempotency outcomes must be written into ops_audit:
- IDEMPOTENCY_HIT
- IDEMPOTENCY_CONFLICT
- IDEMPOTENCY_IN_PROGRESS (if applicable)
- IDEMPOTENCY_FINISH_OK

## Evidence
- Verify script: `anchor-backend/ops/verify_phase311_idempotency_audit.sh`
- Verify log: `/tmp/anchor_phase311_verify_last.log`

## Acceptance
From the verify log:
- `health=OK`
- `IDEM_SAME_2XX=YES`
- `IDEM_CONFLICT_409=YES`
- `PASS: phase311 idempotency audit`

From API:
- `GET /ops/audit?limit=200` includes `IDEMPOTENCY_*` and includes the test idempotency key `phase311-*`.

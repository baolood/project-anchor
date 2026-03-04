# VERIFY phase310 (idempotency keys)

## Acceptance
- /health 200
- `idempotency_keys` table exists
- POST /commands with same `X-Idempotency-Key` and same JSON payload returns identical response body
- POST /commands with same key but different payload returns 409 `IDEMPOTENCY_KEY_CONFLICT`

## Evidence
- `/tmp/anchor_phase310_verify_last.log`

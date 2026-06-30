# Hardened ORDER:testnet One-Shot Execution Script Validation Closeout V1

## 1. Result

- validation closeout prepared: YES
- target script: `scripts/one_shot_order_testnet_invocation.sh`
- validation script: `scripts/check_hardened_order_testnet_one_shot_invocation.sh`
- baseline integration: YES
- before-window fixture blocks before POST: YES
- expired-window fixture blocks before POST: YES
- missing-env fixture blocks before POST: YES
- valid-window fixture remains dry-run by default: YES
- fixed idempotency key preserved: YES
- real external request sent: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

## 2. What Was Verified

The validation script runs only offline fixtures against the hardened one-shot
invocation script.

It verifies that:

- `WINDOW_NOT_OPEN_YET` exits non-zero before any POST branch
- `WINDOW_EXPIRED` exits non-zero before any POST branch
- missing window environment exits non-zero before any POST branch
- a valid window fixture reaches only the dry-run branch unless `--execute` is
  explicitly supplied
- the first bounded idempotency key remains fixed as
  `testnet:ops_manual:BTCUSDT:BUY:4:first-bounded-request:v1`

## 3. Safety Boundary

This closeout does not authorize an execution window.

It does not:

- fill operator authorization
- grant window authorization
- send a real external request
- execute canary
- authorize go-live
- authorize live trading

## 4. Baseline Hook

`scripts/check_local_box_baseline.sh` now runs:

```bash
bash scripts/check_hardened_order_testnet_one_shot_invocation.sh
```

This keeps the time-window stop behavior under the same local/CI baseline used
by the rest of the Project Anchor go-live guardrail stack.

## 5. Remaining Blocker

The current blocker remains:

```text
OPERATOR_WINDOW_REOPEN_AUTHORIZATION_NOT_FILLED
```

The project may now move to an operator authorization result only after the
operator explicitly fills the reopen authorization fields.

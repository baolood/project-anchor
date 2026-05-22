# Testnet command contract V1

**Status:** contract draft only - no implementation, no credentials, no testnet execution, no live trading approval.

**Owner:** **baolood** (Release / Engineering / Operations lead, interim).

**Date:** 2026-05-22

**Pairs with:**

- `docs/TESTNET_READINESS_GAP_REVIEW_V1.md`
- `docs/contracts/command.schema.json`
- `docs/adr/ADR-0001-command-domain-contract.md`
- `docs/adr/ADR-0002-command-state-machine.md`
- `docs/DRY_RUN_SMOKE_RUNBOOK_V1.md`

## 1. Decision

Testnet order execution must use the existing domain Command model and must remain distinguishable from both dry-run and live trading.

The V1 domain command shape is:

```text
Command.type: ORDER
Command.payload.execution_mode: testnet
```

`execution_mode=live` is not part of this contract and must be rejected before any command is persisted or executed.

This document does not create an endpoint, does not add an executor, does not add secrets, and does not permit a real exchange call.

## 2. Domain command shape

The persisted Command must continue to satisfy `docs/contracts/command.schema.json`.

```json
{
  "id": "order-<uuid-or-equivalent>",
  "type": "ORDER",
  "status": "PENDING",
  "payload": {
    "execution_mode": "testnet",
    "market": "binance_testnet",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "notional": "4",
    "order_type": "market",
    "time_in_force": null,
    "limit_price": null,
    "stop_price": "68000",
    "source": "trade_gate_v1",
    "idempotency_key": "testnet-order-<stable-key>",
    "risk_snapshot_id": null,
    "reason": "Trade Gate approved SIMULATE_ONLY to testnet progression.",
    "created_by": "baolood"
  },
  "result": null,
  "error": null
}
```

Notes:

- `id` may use the existing `order-...` prefix convention, but the prefix is not the execution authority.
- `type` is the worker action lookup key and must stay `ORDER` for order intent.
- `payload.execution_mode` is the safety boundary that separates `testnet` from `dry_run` and future `live`.
- Transport endpoints may wrap this shape, but they must not change the domain semantics.

## 3. Required payload fields

| Field | Required | Allowed values / format | Rule |
|-------|----------|-------------------------|------|
| `execution_mode` | yes | `testnet` only | Reject missing, `dry_run`, `paper`, `live`, or unknown values for this contract |
| `market` | yes | explicit testnet venue, e.g. `binance_testnet` | Must not point at a live venue |
| `symbol` | yes | uppercase market symbol, initially `BTCUSDT` | Must match risk policy allowlist |
| `side` | yes | `BUY` or `SELL` | Case-sensitive |
| `notional` | yes | positive decimal string | Reject bool, zero, negative, non-decimal |
| `order_type` | yes | `market` or `limit` | V1 implementation may support only `market`, but contract names both |
| `idempotency_key` | yes | non-empty stable string | Required for safe retry / duplicate suppression |
| `source` | yes | `trade_gate_v1` or `ops_manual` | Records where intent came from |
| `created_by` | yes | operator/user identifier | Required for audit |
| `stop_price` | conditional | positive decimal string | Required when risk policy needs single-trade risk calculation |
| `limit_price` | conditional | positive decimal string or null | Required when `order_type=limit` |
| `time_in_force` | conditional | `GTC`, `IOC`, `FOK`, or null | Required when venue/order type requires it |
| `risk_snapshot_id` | optional | string or null | Links to recorded risk context when available |
| `reason` | optional | non-empty string | Human-readable audit context |

## 4. Rejection rules

Reject before persistence when:

- `execution_mode` is missing or is not exactly `testnet`.
- `execution_mode` is `live`.
- `market` is missing or names a live venue.
- `idempotency_key` is missing.
- `symbol`, `side`, `notional`, or `order_type` is invalid.
- `order_type=limit` and `limit_price` is missing.
- The request attempts to include API key material, secret values, or withdrawal-related fields.
- The request attempts to bypass risk, kill switch, command state machine, or event logging.

Expected rejection response shape for future transport endpoints:

```json
{
  "status": "error",
  "error": "TESTNET_CONTRACT_REJECTED",
  "reason": "<machine-readable reason>"
}
```

No rejected request should create a Command row.

## 5. Idempotency

`idempotency_key` is required for every testnet command.

Rules:

- Repeating the same `idempotency_key` with the same payload should return the first `command_id`.
- Repeating the same `idempotency_key` with a materially different payload should be rejected.
- The idempotency record must include first seen time, last seen time, and first command id.
- The key must not contain secrets.

Recommended key shape:

```text
testnet:<source>:<symbol>:<side>:<notional>:<client-generated-uuid>
```

## 6. State machine

Testnet commands must follow ADR-0002 exactly:

```text
PENDING -> PROCESSING -> DONE
                    \-> FAILED
```

Rules:

- UI may create/read only; it must not mutate status.
- Worker must atomically claim before external execution.
- `FAILED` is terminal and must include `error`.
- `DONE` is terminal and may include `result`.
- Retry is a new command or a future explicit reset mechanism, not an ad-hoc state rollback.

## 7. Required event evidence

Every accepted testnet command must be inspectable through:

```text
/ops -> /commands -> /commands/[id]
```

Expected event path for allowed commands:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_ACCEPTED | TESTNET_EXECUTOR_REJECTED
ACTION_OK | ACTION_FAIL
MARK_DONE | MARK_FAILED
```

Minimum compatibility with the current dry-run smoke event model:

- `PICKED` must exist.
- `POLICY_ALLOW` or `POLICY_BLOCK` must exist.
- `ACTION_OK` or `ACTION_FAIL` must exist.
- `MARK_DONE` or `MARK_FAILED` must exist.

If V1 implementation does not add new event types yet, it must still provide equivalent evidence in existing event payloads before the smoke can pass.

## 8. Kill switch requirements

The worker or executor boundary must check kill switch state immediately before the testnet external call.

Required behavior:

- Kill switch ON before claim: command must not reach external executor.
- Kill switch ON after claim but before external call: command must fail safe before external executor.
- Failure reason must be explicit, e.g. `KILL_SWITCH_ON`.
- Event evidence must show the block.

No testnet implementation is accepted unless a smoke proves kill switch blocks the executor boundary.

## 9. Result and error shape

On `DONE`, `result` should include:

```json
{
  "ok": true,
  "execution_mode": "testnet",
  "market": "binance_testnet",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "notional": "4",
  "testnet_order_id": "<redacted-or-synthetic-id>",
  "external_status": "<venue-status>",
  "ts": "<iso8601>"
}
```

On `FAILED`, `error` should be one of:

```text
TESTNET_CONTRACT_REJECTED
RISK_HARD_LIMITS_SINGLE_TRADE_RISK_EXCEEDED
POLICY_BLOCK
KILL_SWITCH_ON
TESTNET_EXECUTOR_REJECTED
TESTNET_EXECUTOR_TIMEOUT
TESTNET_EXECUTOR_AUTH_FAILED
TESTNET_EXECUTOR_NETWORK_ERROR
UNKNOWN_TYPE
ACTION_EXCEPTION
```

`UNKNOWN_TYPE` is never an acceptable final state for a release candidate; it means worker/action registration is wrong or stale.

## 10. Security boundary

This contract permits testnet planning only.

Before any testnet key is used:

- Key storage must be documented outside git.
- Key must be testnet-only.
- Withdrawal permission must be disabled.
- Rotation path must be documented.
- No-plaintext scan must be part of smoke evidence.

This contract does not permit live credentials, live exchange endpoints, or live order placement.

## 11. Acceptance for this contract

```text
contract file created: PASS
Command.type ORDER preserved: PASS
execution_mode testnet required: PASS
execution_mode live rejected: PASS
idempotency defined: PASS
state machine aligned with ADR-0002: PASS
command detail evidence path defined: PASS
kill switch requirement defined: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

## 12. Next single task

Recommended next task:

```text
Testnet Secrets Custody V1
```

Scope:

- docs only
- define where testnet credentials live
- define least-privilege requirements
- define rotation and no-plaintext scan evidence
- no API key value
- no backend / worker / risk implementation

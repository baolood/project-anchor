# Testnet stub runbook V1

**Status:** active review runbook for the local testnet stub event semantics.

**Owner:** **baolood** (Engineering / Operations lead, interim).

**Scope:** this runbook explains how to read the current **testnet stub** event chain in `commands_domain`.

It covers:

```text
ORDER command
-> execution_mode=testnet
-> local stub result
-> command events
```

It does **not** enable:

- external testnet API calls
- API key usage
- real exchange testnet orders
- live trading

## 1. What `TESTNET_EXECUTOR_STUB` means

`TESTNET_EXECUTOR_STUB` now has a strict meaning:

```text
the ORDER command reached the successful local testnet stub path
and the result was marked as testnet_stub=true
```

This event is **success-only**.

It must not appear for:

- invalid payload
- rejected payload
- failed action
- failed mark path
- live execution attempt

## 2. When `TESTNET_EXECUTOR_STUB` should appear

Expected conditions:

- `Command.type == ORDER`
- `payload.execution_mode == "testnet"`
- action result is `ok: true`
- result includes:
  - `execution_mode: "testnet"`
  - `testnet_stub: true`
  - `external_call: false`

Expected success event chain:

```text
PICKED
TESTNET_EXECUTOR_STUB
ACTION_OK
MARK_DONE
```

This means:

- worker claimed the command
- local testnet stub path was actually reached
- action returned success
- command was finalized as `DONE`

## 3. When `ACTION_FAIL` / `MARK_FAILED` should appear

Expected failure chain for invalid or rejected testnet payload:

```text
PICKED
ACTION_FAIL
MARK_FAILED
```

Common reasons:

- missing `idempotency_key`
- invalid `market`
- invalid `order_type`
- missing `limit_price` for `order_type=limit`
- forbidden secret field such as `api_key`
- `execution_mode=live`

In these cases:

```text
TESTNET_EXECUTOR_STUB must NOT appear
```

That absence is important: it tells us the stub path was **not** actually accepted.

## 4. Why failed payload must not write `TESTNET_EXECUTOR_STUB`

If a rejected payload wrote `TESTNET_EXECUTOR_STUB`, it would create a misleading audit trail:

```text
event says "stub executed"
but command actually failed before a valid stub result existed
```

That would make later review ambiguous.

The corrected semantics are:

```text
TESTNET_EXECUTOR_STUB present = success path reached
TESTNET_EXECUTOR_STUB absent + ACTION_FAIL/MARK_FAILED = payload rejected or action failed
```

## 5. How to judge whether testnet stub truly succeeded

Use `/ops -> /commands -> /commands/[id]` and check both status and events.

Minimum accepted success evidence:

```text
status: DONE
events:
- PICKED
- TESTNET_EXECUTOR_STUB
- ACTION_OK
- MARK_DONE
result.execution_mode: testnet
result.testnet_stub: true
result.external_call: false
```

Minimum accepted rejection evidence:

```text
status: FAILED
events:
- PICKED
- ACTION_FAIL
- MARK_FAILED
no TESTNET_EXECUTOR_STUB event
```

## 6. What this still does not prove

Even when success evidence is present, it still does **not** prove:

- real testnet credentials exist
- real testnet HTTP was called
- real exchange testnet accepted an order
- kill switch passed a real executor boundary
- live trading is allowed

Current meaning is narrower:

```text
the local testnet stub path and its event semantics are correct
```

## 7. Review checklist

Use this quick checklist during review:

```text
[Testnet Stub Review]
command type is ORDER: PASS/FAIL
execution_mode is testnet: PASS/FAIL
status is DONE or FAILED: PASS/FAIL
if DONE, TESTNET_EXECUTOR_STUB exists: PASS/FAIL
if FAILED, TESTNET_EXECUTOR_STUB absent: PASS/FAIL
ACTION_OK / ACTION_FAIL consistent with status: PASS/FAIL
MARK_DONE / MARK_FAILED present: PASS/FAIL
result.external_call is false: PASS/FAIL
API key used: NO
real order placed: NO
live trading: NO-GO
```

## 8. Troubleshooting

| Symptom | Meaning | Next check |
|---------|---------|------------|
| `DONE` but no `TESTNET_EXECUTOR_STUB` | event semantics regression | inspect runner event logic |
| `FAILED` and `TESTNET_EXECUTOR_STUB` exists | false-positive success event | treat as bug |
| `UNKNOWN_TYPE` | worker/action registration problem | inspect action registry and worker build |
| `ACTION_FAIL` with `LIVE_EXECUTION_DISABLED` | live request was correctly blocked | keep NO-GO |
| `ACTION_FAIL` with `TESTNET_CONTRACT_REJECTED` | payload failed contract validation | inspect payload fields |

## 9. Acceptance record

```text
[Testnet Stub Event Review]
date:
parent commit:
command_id:
status:
event_chain:
stub_success_semantics: PASS/FAIL
failed_payload_semantics: PASS/FAIL
external_call: false
api_key_used: NO
real_order: NO
live trading: NO-GO
```

This runbook is for event interpretation only. It does not authorize moving to real testnet execution.

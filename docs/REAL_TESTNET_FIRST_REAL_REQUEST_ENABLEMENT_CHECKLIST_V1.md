# Real Testnet first real request enablement checklist V1

**Status:** enablement checklist only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-23

**Scope:** compress the exact runtime toggles, reviewer checks, and operator signoff steps required immediately before switching the canonical testnet executor path from `mock` to `real` for one bounded first request:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This checklist does not authorize the switch. It standardizes the last pre-enable ritual before any real external testnet request is attempted.

## 1. Decision

The first real request remains blocked unless this checklist is executed in order and every required item is marked complete.

If any required item is:

- missing
- ambiguous
- unverifiable
- contradicted by `/commands/[id]` evidence

then result is:

```text
BLOCKED - stay on mock or fail-closed posture
```

## 2. Fixed enablement boundary

This checklist applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be used for:

```text
legacy QUOTE + BINANCE_TESTNET
TESTNET_EXECUTOR_STUB
live trading
```

## 3. Required runtime toggles

Before the first real request, confirm all of these runtime statements explicitly:

1. `TESTNET_EXECUTOR_MODE=real` is being set intentionally for this bounded request only.
2. `TESTNET_EXECUTOR_MODE` is not inherited from an old shell or deploy drift.
3. The guarded real-wire posture is understood:
   - `TESTNET_REAL_WIRE_DISABLED` must still be reachable if real wire is not explicitly enabled.
4. Canonical env naming remains:
   - `TESTNET_EXCHANGE_BASE_URL`
   - `TESTNET_EXCHANGE_API_KEY`
   - `TESTNET_EXCHANGE_API_SECRET`
   - `TESTNET_EXCHANGE_KEY_ID`
5. No legacy `BINANCE_*` runtime naming is being treated as the canonical source.

If any toggle cannot be stated plainly, do not switch.

## 4. Required runtime safety checks

Mark each item before the first real request:

- canonical host maps to the exact allowlisted HTTPS origin
- credential presence can be proven without exposing secrets
- kill switch authoritative merged state is readable
- `mock` path still works as a retreat option
- `invalid mode` still fails closed
- `real disabled` still fails closed
- `/commands/[id]` still explains:
  - preflight refusal
  - mocked external attempt
  - real external attempt

These are not optional. If one is unknown, status is `BLOCKED`.

## 5. Required command-shape checks

The first real request command must satisfy all of these:

- `type=ORDER`
- `payload.execution_mode=testnet`
- `market` is the expected testnet venue
- `symbol` is intentionally chosen and already known from earlier docs/smokes
- `side` is explicit
- `notional` is intentionally small
- `order_type` is explicit
- `stop_price` is present and positive
- `source` is explicit, such as `ops_manual`
- `created_by` is explicit
- `idempotency_key` is explicit and unique

If the command is not deliberately narrow and reviewable, do not enable `real`.

## 6. Required reviewer signoff statements

The reviewer must explicitly confirm all of these statements:

1. “This is the canonical ORDER testnet path.”
2. “Legacy QUOTE behavior is not being used as proof.”
3. “The path can still fail before signed HTTP through contract, host safety, credential, or kill-switch refusal.”
4. “The path can still be explained through `/ops -> /commands -> /commands/[id]`.”
5. “If the request behaves unexpectedly, we will retreat to `mock` or fail-closed posture before a second attempt.”
6. “Live trading remains NO-GO.”

If any statement cannot be signed off cleanly, do not switch.

## 7. Required negative evidence expectations

Before enablement, everyone involved must understand these must remain impossible or absent:

- `TESTNET_EXECUTOR_STUB` on a real-attempt path
- preflight refusal with external-attempt evidence
- `external_order_id` without `TESTNET_EXECUTOR_ACCEPTED`
- secret material in result or event payload
- silent fallback from `real` to legacy QUOTE path
- ambiguous host/origin identity

If the team cannot describe these negative evidence rules, the checklist is incomplete.

## 8. First-request stop triggers

Stop immediately and retreat to `mock` or fail-closed posture if any of these occur:

- missing `TESTNET_EXECUTOR_REQUESTED`
- missing `TESTNET_EXECUTOR_ACCEPTED` or `TESTNET_EXECUTOR_REJECTED`
- contradictory event chain vs page explanation
- unexpected `failure_family`
- malformed or missing `external_order_id` on supposed acceptance
- configured origin does not match expected host label
- signs of secret leakage in review evidence
- any hint that a second attempt would be “just a quick retry”

No second real attempt should happen until the first anomaly is reviewed.

## 9. Minimum post-switch review path

After the first real request, review must happen in this order:

```text
/ops
-> /commands
-> /commands/[id]
```

Review must answer:

- was this definitely real mode?
- did request evidence cross the external boundary?
- was the final state `DONE` or `FAILED`?
- was the normalized success/failure family reviewable?
- is retreat required before any second request?

Do not finalize from terminal output alone.

## 10. Enablement result labels

Use exactly one result:

### `PASS`

Only if:

- every runtime toggle is explicit
- every safety check is complete
- command shape is narrow and reviewable
- reviewer signoff statements are all accepted
- stop triggers are understood
- live trading remains `NO-GO`

### `BLOCKED`

If:

- any check is unknown
- any runtime toggle is ambiguous
- any negative evidence rule is unclear
- retreat posture is not immediate

### `FAIL`

If:

- enablement is attempted without this checklist
- the actual runtime posture contradicts the signed-off posture
- a real request is attempted under ambiguous mode or host conditions

## 11. Minimal next bounded round

After this checklist, the next natural bounded round is:

```text
Real Testnet First Real Request Operator Signoff Record V1
```

Scope:

```text
docs-only
capture the exact record format for who enabled, who reviewed,
which host/command was used, and whether the result was PASS/BLOCKED/FAIL
```

# Real testnet real transport contract V1

**Status:** transport contract only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Security lead, interim).

**Date:** 2026-05-23

**Scope:** define the precise helper contract for the first real credential-backed testnet transport path under the canonical executor boundary:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not enable the transport. It fixes the input/output and review-safe evidence contract the helper must satisfy before real transport is allowed.

## 1. Decision

The first real transport contract is a narrow helper contract only.

It must define:

- what runner passes into the real helper
- what the helper may return on success
- what the helper may return on failure
- which fields become event evidence
- which fields must never leak

It must not:

- redesign command routing
- change preflight semantics
- invent replay behavior
- broaden into a generic exchange SDK

## 2. Contract objective

The helper contract exists to answer one question:

```text
if runner switches from mock to real,
what exact boundary object crosses into transport,
and what exact normalized object comes back?
```

Without this, the real-wire step would still be too implicit.

## 3. Input contract

Runner should pass one normalized input object into the helper.

Minimum required fields:

```text
command_id
attempt
execution_mode=testnet
market
symbol
side
notional
order_type
source
created_by
stop_price
idempotency_key
host_label
configured_origin
canonical_path
key_id_present
```

Notes:

- these fields arrive only after contract, risk, kill switch, host safety, and credential-presence checks
- `canonical_path` must stay `ORDER:testnet`
- the helper must not re-derive these fields from raw UI payload

## 4. Input semantic rules

The helper may assume:

- `execution_mode == testnet`
- host safety already selected an allowed origin
- credentials are present in runtime env
- `idempotency_key` belongs to the logical command intent

The helper may not assume:

- live execution is allowed
- replay is authorized
- background retry is allowed

## 5. Real request contract

For the first real transport slice, the helper may perform only:

- one bounded signed request
- to one canonical testnet origin
- using canonical `TESTNET_EXCHANGE_*` env names

It must not:

- send more than one outbound attempt
- fallback to another host
- mutate payload meaning mid-flight
- emit DB writes directly

## 6. Success return contract

On accepted upstream result, helper should return a normalized success object shaped like:

```json
{
  "ok": true,
  "result": {
    "ok": true,
    "type": "order",
    "execution_mode": "testnet",
    "market": "binance_testnet",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "notional": 4.0,
    "order_type": "market",
    "source": "trade_gate_v1",
    "created_by": "baolood",
    "stop_price": 68000.0,
    "idempotency_key": "testnet:...",
    "host_label": "binance_futures_testnet",
    "external_order_id": "<exchange order id>",
    "external_status": "<normalized status>",
    "ts": 0
  },
  "error": null
}
```

Minimum semantic rules:

- `external_order_id` must exist
- `execution_mode` must remain `testnet`
- `host_label` must stay aligned with the preflight-selected venue
- `idempotency_key` must remain the same logical intent key

## 7. Failure return contract

On real external failure, helper should return a normalized failure object shaped like:

```json
{
  "ok": false,
  "result": null,
  "error": {
    "code": "TESTNET_EXECUTOR_AUTH_FAILED",
    "failure_family": "TESTNET_EXECUTOR_AUTH_FAILED",
    "failure_reason": "normalized review-safe reason",
    "gate": "external_executor",
    "external_request_started": true,
    "external_order_id_present": false,
    "execution_mode": "testnet",
    "host_label": "binance_futures_testnet",
    "configured_origin": "https://testnet.binancefuture.com",
    "canonical_path": "ORDER:testnet",
    "ts": 0
  }
}
```

Minimum semantic rules:

- `failure_family` must point into the approved taxonomy
- `failure_reason` must be human-comprehensible
- `external_request_started` must reflect that the request crossed the transport boundary
- `canonical_path` must remain visible

## 8. Pre-transport fail-closed contract

If `TESTNET_EXECUTOR_MODE=real` is selected but real transport is still guarded off, helper may return a fail-closed boundary refusal such as:

- `TESTNET_REAL_WIRE_DISABLED`
- `TESTNET_REAL_WIRE_NOT_IMPLEMENTED`

Rules:

- `external_request_started` must be `false`
- no `TESTNET_EXECUTOR_REQUESTED`
- no `external_order_id`

This keeps the helper safely usable before real credentials are actually exercised.

## 9. Event payload contract

When runner persists events around the helper, the transport contract must support these review-safe payloads:

### `TESTNET_EXECUTOR_REQUESTED`

Required:

- `attempt`
- `execution_mode`
- `host_label`
- `configured_origin`
- `canonical_path`
- `external_request_started=true`
- `executor_mode_label`
- `timeout_policy_label`

### `TESTNET_EXECUTOR_ACCEPTED`

Required:

- `attempt`
- `execution_mode`
- `host_label`
- `configured_origin`
- `canonical_path`
- `external_request_started=true`
- `external_order_id`
- `external_status`

### `TESTNET_EXECUTOR_REJECTED`

Required:

- `attempt`
- `execution_mode`
- `host_label`
- `configured_origin`
- `canonical_path`
- `external_request_started=true`
- `failure_family`
- `failure_reason`

## 10. Review-safe field rules

The helper may expose these review-safe fields:

- `host_label`
- `configured_origin`
- `external_order_id`
- `external_status`
- `failure_family`
- `failure_reason`
- `key_id_present`
- `executor_mode_label`
- `timeout_policy_label`

The helper must not expose:

- API key
- API secret
- raw HMAC/signature
- raw authorization header
- raw secret manager token

## 11. Canonical env usage rule

The helper must read only canonical real-testnet names:

- `TESTNET_EXCHANGE_API_KEY`
- `TESTNET_EXCHANGE_API_SECRET`
- `TESTNET_EXCHANGE_BASE_URL`
- `TESTNET_EXCHANGE_KEY_ID`

Legacy names may be supported only behind an explicit adapter layer outside the helper contract.

## 12. Timeout and replay labels

The helper contract should support review-safe labels such as:

- `timeout_policy_label=single_attempt_v1`
- `executor_mode_label=real`

These labels matter because later review must distinguish:

- mock vs real
- bounded single-attempt vs any future retry-capable posture

## 13. Negative evidence contract

The helper contract must preserve these meanings:

### local/preflight refusal

- no helper request call
- no `TESTNET_EXECUTOR_REQUESTED`
- no `external_order_id`

### real transport failure

- helper crossed transport boundary
- `TESTNET_EXECUTOR_REQUESTED` exists
- `TESTNET_EXECUTOR_REJECTED` exists
- `external_order_id` may be absent

### real transport success

- helper crossed transport boundary
- `TESTNET_EXECUTOR_REQUESTED` exists
- `TESTNET_EXECUTOR_ACCEPTED` exists
- `external_order_id` exists

## 14. Non-goals for this contract

This contract does not yet decide:

- replay implementation
- multiple external attempts
- background reconciliation
- exchange-specific abstraction beyond the first bounded helper
- live trading semantics

Those remain separate rounds.

## 15. Acceptance for this contract

This transport contract is complete only if the team can answer:

- what exact object runner passes into real transport
- what exact normalized objects success and failure must return
- what event payload fields are mandatory
- what secrets must never leak
- how to tell local refusal from real transport attempt

That answer is now fixed by this document.

## 16. Next recommended round

Next recommended round:

```text
Real Testnet Real Wire Transport Stub Implementation V1
```

That round may begin code again by making the new helper emit full real-mode event/result contracts under guarded conditions, still before any real credential-backed outbound call is actually allowed.

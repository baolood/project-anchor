# Testnet stub review checklist V1

**Status:** quick review checklist for the local testnet stub path.

**Owner:** **baolood** (Engineering / Operations lead, interim).

**Use this when:** you want a fast PASS/FAIL review of a testnet stub command without rereading the full runbook.

**Pairs with:**

- `docs/TESTNET_STUB_RUNBOOK_V1.md`
- `docs/TESTNET_COMMAND_CONTRACT_V1.md`

## 1. Accepted payload shape

A payload is review-ready for the current stub only if all of these are true:

```text
type: ORDER
execution_mode: testnet
market: binance_testnet
symbol: BTCUSDT
side: BUY | SELL
notional: positive
order_type: market | limit
idempotency_key: present
source: trade_gate_v1 | ops_manual
created_by: present
stop_price: present and > 0
```

If `order_type=limit`, `limit_price` must also be present.

## 2. Rejected payload signs

Reject the payload review if any of these are true:

```text
execution_mode: live
missing idempotency_key
invalid market
invalid source
missing created_by
missing or invalid stop_price
forbidden field like api_key / secret / secret_key / passphrase
```

Expected result for rejected payload:

```text
status: FAILED
events:
- PICKED
- ACTION_FAIL
- MARK_FAILED
```

`TESTNET_EXECUTOR_STUB` must not appear.

## 3. Success path signs

Treat the stub as truly successful only if all of these are true:

```text
status: DONE
events include PICKED
events include TESTNET_EXECUTOR_STUB
events include ACTION_OK
events include MARK_DONE
result.execution_mode == testnet
result.testnet_stub == true
result.external_call == false
result echoes source
result echoes created_by
result echoes stop_price
```

## 4. Failure path signs

Treat the stub as correctly rejected only if all of these are true:

```text
status: FAILED
events include PICKED
events include ACTION_FAIL
events include MARK_FAILED
events do not include TESTNET_EXECUTOR_STUB
error is meaningful
```

## 5. Audit meaning of fields

- `source`: tells us whether the command came from `trade_gate_v1` or `ops_manual`.
- `created_by`: tells us which operator/user initiated the stub intent.
- `stop_price`: lets later reviewers compare the stub payload against intended trade-risk framing.

These fields are there for traceability, not to authorize real trading.

## 6. Fast review card

```text
[Testnet Stub Quick Review]
type ORDER: PASS/FAIL
execution_mode testnet: PASS/FAIL
source allowlist valid: PASS/FAIL
created_by present: PASS/FAIL
stop_price positive: PASS/FAIL
if DONE, TESTNET_EXECUTOR_STUB present: PASS/FAIL
if FAILED, TESTNET_EXECUTOR_STUB absent: PASS/FAIL
ACTION_OK/ACTION_FAIL consistent: PASS/FAIL
MARK_DONE/MARK_FAILED present: PASS/FAIL
external_call false: PASS/FAIL
API key used: NO
external API called: NO
real order placed: NO
live trading: NO-GO
```

## 7. What this checklist does not mean

Passing this checklist does **not** mean:

- a real exchange testnet API was called
- API keys are configured
- live trading is allowed
- risk and kill switch have been proven against a real external executor

It only means:

```text
the current local testnet stub path and its audit/event semantics look correct
```

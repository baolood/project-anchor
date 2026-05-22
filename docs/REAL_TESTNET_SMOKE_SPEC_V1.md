# Real testnet smoke spec V1

**Status:** smoke specification only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** define the minimum acceptable smoke for the future canonical real testnet path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize implementation or execution. It only defines what a real testnet smoke must prove before the path can be considered minimally credible.

## 1. Decision

The first accepted real testnet smoke must run only through:

```text
ORDER + execution_mode=testnet
```

It must not use:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
```

It must not reuse the local-only stub as proof of real external readiness.

## 2. Smoke objective

The smoke exists to prove one narrow claim:

```text
a valid ORDER testnet command can cross the real testnet executor boundary,
reach a real testnet upstream,
return normalized evidence,
and land in /commands/[id] as a reviewable DONE or FAILED result
without touching live trading
```

This is not a performance test, not a load test, and not approval for live execution.

## 3. Preconditions

The smoke must remain blocked unless all of these are true:

```text
canonical path = ORDER + execution_mode=testnet
legacy QUOTE path is not used
canonical TESTNET_EXCHANGE_* env contract is wired
credentials are testnet-only and stored outside git
kill switch behavior at the real executor boundary is defined
command detail review path is available
R-001 remains OPEN and understood
R-002 remains OPEN and understood
live trading remains NO-GO
```

## 4. Canonical input shape

Minimum smoke input should be a single manually traceable order intent with fields like:

```json
{
  "type": "ORDER",
  "payload": {
    "execution_mode": "testnet",
    "market": "binance_testnet",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "notional": 4.0,
    "order_type": "market",
    "stop_price": 68000.0,
    "source": "ops_manual",
    "created_by": "baolood",
    "idempotency_key": "testnet-smoke-<date>-<seq>"
  }
}
```

Notes:

- use the canonical `ORDER` command shape only
- keep notional small and clearly non-live
- use a unique idempotency key for every smoke
- do not embed any key or secret in the payload

## 5. What the smoke must prove

At minimum the smoke must prove:

```text
canonical ORDER path claimed the command
contract validation accepted the payload
policy/risk allowed the request to reach executor boundary
kill switch was checked before signed HTTP
a real testnet upstream request was attempted
upstream response or upstream rejection was normalized
/commands/[id] shows enough evidence for human review
no live host was used
```

## 6. Required event evidence

The smoke must produce an auditable event chain.

Minimum success evidence target:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_ACCEPTED
ACTION_OK
MARK_DONE
```

Minimum upstream-failure evidence target:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
TESTNET_EXECUTOR_REQUESTED
TESTNET_EXECUTOR_REJECTED
ACTION_FAIL
MARK_FAILED
```

Minimum kill-switch-block evidence target:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
ACTION_FAIL
MARK_FAILED
```

with a normalized reason proving no signed HTTP was sent after kill switch refusal.

The smoke must **not** treat this event as real-executor evidence:

```text
TESTNET_EXECUTOR_STUB
```

That event remains stub-only.

## 7. Result evidence requirements

Successful smoke should normalize and preserve fields such as:

```text
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
external_order_id
external_status
ts
```

Failed smoke should still preserve enough evidence to distinguish:

```text
contract rejection
kill switch refusal
upstream auth failure
upstream validation failure
network timeout
unexpected upstream error
```

## 8. Review path

The human review path for the smoke remains:

```text
/ops
-> /commands
-> /commands/[id]
```

Acceptance should not rely on terminal output alone.

The command detail page must let the reviewer answer:

```text
was this the ORDER testnet path?
did it cross the real executor boundary?
did kill switch get checked?
did upstream accept or reject it?
was the final state DONE or FAILED?
was any live path touched?
```

## 9. PASS criteria

The smoke is a PASS only if all of these are true:

```text
command path = ORDER + execution_mode=testnet
canonical TESTNET_EXCHANGE_* env family used
real upstream request attempted or explicitly blocked by kill switch
event chain matches the expected family
result/error normalized
reviewer can inspect command detail evidence
no TESTNET_EXECUTOR_STUB misuse
no live host used
no API key stored in git
live trading remains NO-GO
```

## 10. FAIL criteria

The smoke is a FAIL if any of these happen:

```text
legacy QUOTE path used
stub-only evidence presented as real smoke proof
live hostname or ambiguous host used
kill switch not evidenced before external request
idempotency_key missing
command detail lacks enough evidence
env naming falls back to undocumented contract
payload carries secrets
result cannot distinguish upstream rejection from local validation failure
```

## 11. Recommended bounded execution order

When real testnet implementation eventually starts, the smoke should be attempted in this order:

1. Kill-switch-block smoke
2. Upstream-auth-or-validation failure smoke
3. Small successful acceptance smoke

This order is safer because it proves the fail-safe boundary before proving upstream acceptance.

## 12. What not to do

- Do not run the first real smoke through the legacy `QUOTE` path.
- Do not treat a green stub run as equivalent to real smoke.
- Do not wire testnet keys before the executor boundary exists.
- Do not broaden scope into live trading, funding, or deploy changes.
- Do not close R-001 or R-002 based on smoke alone.

## 13. Recommended next bounded round

After this spec, the natural next round is:

```text
Kill Switch Real Boundary Check V1
```

Scope:

```text
docs or design-first verification plan
prove kill switch blocks real testnet executor attempts before signed HTTP
no live trading
```

## 14. Acceptance for this spec

```text
canonical smoke path fixed to ORDER + execution_mode=testnet: PASS
stub evidence excluded from real smoke proof: PASS
required event families stated: PASS
review path fixed to /ops -> /commands -> /commands/[id]: PASS
kill switch proof included: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

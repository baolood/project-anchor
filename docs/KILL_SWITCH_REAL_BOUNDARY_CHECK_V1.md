# Kill switch real boundary check V1

**Status:** verification design only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** define how Project Anchor must prove that the kill switch blocks the future canonical real testnet executor boundary before any signed HTTP request.

Canonical target path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not implement the boundary check. It defines the acceptance evidence required before the real testnet path can be treated as minimally safe.

## 1. Decision

The kill switch proof must be attached to the canonical future path:

```text
ORDER + execution_mode=testnet
```

It must not be satisfied by:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
```

It must not be satisfied by:

```text
TESTNET_EXECUTOR_STUB
```

because stub evidence does not prove that a real external executor was prevented from sending signed HTTP.

## 2. Objective

The check exists to prove one narrow claim:

```text
when kill switch is ON,
the canonical ORDER testnet path reaches the executor boundary gate,
records explicit kill-switch evidence,
and fails safe before any signed external request is sent
```

This is not a general worker smoke, not a live trading approval, and not a substitute for the full real testnet smoke.

## 3. Why this check is separate

Real testnet safety depends on one strict boundary:

```text
validated command
-> policy/risk pass
-> kill switch decision
-> external signed HTTP
```

If kill switch proof is vague, reviewers cannot tell whether:

- the command was blocked before external request
- the command failed for some unrelated validation reason
- the executor had already sent something upstream

That ambiguity is unacceptable for the first real testnet rollout.

## 4. Preconditions

This check must remain blocked unless all of these are true:

```text
canonical path fixed to ORDER + execution_mode=testnet
real executor boundary defined
canonical TESTNET_EXCHANGE_* env contract chosen
review path /ops -> /commands -> /commands/[id] available
kill switch control endpoint or equivalent operator control available
R-001 remains OPEN and understood
R-002 remains OPEN and understood
live trading remains NO-GO
```

## 5. Required operator setup

The future boundary check must use:

```text
kill switch ON before command submission
single traceable ORDER testnet input
unique idempotency_key
explicit source
explicit created_by
valid stop_price
testnet-only host configuration
```

The check must not depend on:

- ad hoc shell output as the only evidence
- inferred hostnames
- legacy QUOTE path behavior
- secret fields inside payload

## 6. Canonical verification input

Minimum input shape should look like:

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
    "idempotency_key": "kill-switch-check-<date>-<seq>"
  }
}
```

The purpose of this input is not to get `DONE`.
The purpose is to prove safe refusal before external request.

## 7. Required evidence claim

The check must prove all of the following:

```text
command entered the canonical ORDER testnet flow
payload was not rejected for unrelated local contract reasons
kill switch state was checked at the real executor boundary
kill switch refusal happened before signed HTTP
no external order request was sent
failure reason was normalized and reviewable
```

## 8. Event evidence requirements

Minimum target event family for kill-switch refusal:

```text
PICKED
POLICY_ALLOW
KILL_SWITCH_CHECKED
ACTION_FAIL
MARK_FAILED
```

The final error family must clearly indicate kill switch refusal, for example:

```text
KILL_SWITCH_ON
```

Optional future evidence can be added, but the minimal proof must remain easy to read.

## 9. Negative evidence requirements

The check is not valid unless reviewers can also prove the absence of unsafe evidence.

Unsafe evidence that must be absent:

```text
TESTNET_EXECUTOR_REQUESTED after kill switch refusal
TESTNET_EXECUTOR_ACCEPTED
ACTION_OK
MARK_DONE
external_order_id
external_status from real upstream
```

If any of the above appears, the refusal proof fails because the command crossed too far into the real executor path.

## 10. Review path

The reviewer must be able to inspect the result through:

```text
/ops
-> /commands
-> /commands/[id]
```

The command detail page must allow the reviewer to answer:

```text
was this an ORDER testnet command?
did contract/policy pass first?
was kill switch checked?
did failure occur before external request?
is the failure family clearly KILL_SWITCH_ON?
is there any evidence that an upstream request was attempted?
```

## 11. PASS criteria

This check is a PASS only if all of these are true:

```text
canonical ORDER testnet path used
kill switch ON before submission
command not rejected for unrelated contract problem
KILL_SWITCH_CHECKED evidence present
final failure family = KILL_SWITCH_ON (or equivalent normalized refusal)
no TESTNET_EXECUTOR_REQUESTED after refusal
no upstream acceptance evidence
no external_order_id
review path shows enough evidence
live trading remains NO-GO
```

## 12. FAIL criteria

This check is a FAIL if any of these happen:

```text
legacy QUOTE path used
stub-only evidence presented as real boundary proof
command fails for unrelated local validation issue
kill switch checked too early to prove real boundary placement
TESTNET_EXECUTOR_REQUESTED appears before refusal is recorded
upstream acceptance/rejection evidence appears
failure family is ambiguous
review path cannot distinguish boundary refusal from upstream failure
```

## 13. Relationship to the full real testnet smoke

This check is narrower than the full real testnet smoke.

The order should be:

1. kill switch refusal proof
2. upstream auth/validation rejection proof
3. small accepted real testnet smoke

Reason:

```text
prove fail-safe boundary first,
then prove controlled external contact,
then prove small successful acceptance
```

## 14. What not to do

- Do not use a stub-only command and call that real boundary proof.
- Do not use terminal logs alone if `/commands/[id]` cannot show the evidence.
- Do not allow kill switch proof to depend on the legacy QUOTE branch.
- Do not broaden this round into real key wiring or deploy work.
- Do not interpret a PASS here as live trading approval.

## 15. Recommended next bounded round

After this check design, the natural next round is:

```text
Real Testnet Failure Taxonomy V1
```

Scope:

```text
docs-only
define stable failure families for auth, validation, timeout, network, and kill switch
no real key
no live trading
```

## 16. Acceptance for this design

```text
canonical kill switch proof path fixed to ORDER + execution_mode=testnet: PASS
stub evidence excluded: PASS
negative evidence requirements stated: PASS
review path fixed to /ops -> /commands -> /commands/[id]: PASS
safe refusal before signed HTTP required: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

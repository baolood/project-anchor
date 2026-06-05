# Real External Request Window Authorization Reopen Review V1

## 1. Purpose

This artifact reviews whether the project is now structurally ready to ask the
operator to reopen one bounded real external request window.

It does not reopen the window by itself.
It does not run pre-execution checks.
It does not send a real external request.

## 2. Current readiness state

- canonical ORDER:testnet operator endpoint implemented: YES
- final execution packet revisit merged: YES
- exact invocation packet prepared: YES
- hardened one-shot execution script merged: YES
- operator authorization filled now: NO
- window authorization granted now: NO
- real external request authorized now: NO
- canary execution authorized now: NO
- go-live: NO-GO
- live trading: NO-GO

## 3. What is now structurally ready

The following previously missing execution-prep pieces now exist together:

1. canonical operator-facing endpoint
   - `POST /trade-gate/testnet-order-intents`
2. exact invocation surface selected
   - direct backend route on stage host only
3. exact bounded request body fixed
4. exact idempotency key fixed
5. exact evidence capture command set fixed
6. exact retreat / stop sequence fixed
7. hardened one-shot script merged with strict time guard enforcement

This means the project is no longer missing packet shape, packet surface, or
script-level time guard enforcement.

## 4. What remains intentionally blocked

Even with those pieces in place, all of these remain intentionally blocked:

- no operator window is open yet
- no pre-execution check has started yet
- no real external request is authorized yet
- no real external request has been sent
- no canary is authorized
- no go-live is authorized
- no live trading is authorized

This review is therefore about reopen readiness, not about execution.

## 5. Reopen review result

The reopen review result is:

```text
READY FOR OPERATOR REOPEN DECISION
```

Meaning:

- the repo now contains the minimum bounded invocation definition
- the repo now contains script-level hard stop behavior
- the remaining missing step is no longer technical packet definition
- the remaining missing step is explicit operator authorization

## 6. Operator requirements still required

Before any new pre-execution check may begin, the operator still must explicitly
fill and affirm:

- operator identity
- authorization timestamp
- window start
- window end
- target environment
- invocation surface
- maximum request count
- maximum live funds exposure
- live trading authorized
- kill switch verified
- retreat/rollback path verified
- alert receipt path verified
- on-call owner active
- stop conditions accepted
- post-window closeout required
- final operator verdict

## 7. Minimum acceptable reopen posture

Any valid reopen decision must still preserve:

- target environment: `stage / bounded testnet environment only`
- invocation surface:
  - `POST /trade-gate/testnet-order-intents`
- maximum request count: `1`
- maximum live funds exposure: `0`
- live trading authorized: `NO`
- canary execution: `NOT AUTHORIZED`
- go-live: `NO-GO`
- post-window closeout required: `YES`

## 8. What this review changes

This review changes the state from:

```text
not ready to ask for reopen
```

to:

```text
ready to ask for operator reopen decision
```

That is the boundary shift.

It does **not** change the state to:

```text
window reopened
```

or:

```text
precheck may start now
```

## 9. Stable result statement

The correct result statement after this review is:

```text
window reopen review: READY
operator authorization filled: NO
window authorization granted: NO
real external request authorized now: NO
go-live: NO-GO
live trading: NO-GO
```

## 10. Required next artifact

The next required artifact is:

```text
Real External Request Window Operator Authorization Result
```

Only after that artifact is explicitly filled with a real `GRANTED` decision
may the project move into:

```text
Real External Request Window Pre-Execution Check
```

## 11. Explicit non-claims

- This review does not reopen the window.
- This review does not authorize a real external request.
- This review does not start precheck.
- This review does not send a request.
- This review does not authorize canary.
- This review does not authorize go-live.
- This review does not authorize live trading.

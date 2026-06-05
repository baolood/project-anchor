# Real External Request Window Reopen Authorization V1

## 1. Purpose

This document records whether the operator reopens authorization after the exact invocation packet was merged.

It does not send a request by itself.

## 2. Current readiness state

- canonical ORDER:testnet operator endpoint implemented: YES
- exact invocation packet merged: YES
- final execution command shape documented: YES
- real external request sent now: NO
- canary executed now: NO
- go-live: NO-GO
- live trading: NO-GO

## 3. Required operator fields

The operator must fill these before any new precheck window:

- operator:
- authorization timestamp:
- window start:
- window end:
- target environment:
- invocation surface:
- maximum request count:
- maximum live funds exposure:
- live trading authorized:
- kill switch verified:
- retreat/rollback path verified:
- alert receipt path verified:
- on-call owner active:
- stop conditions accepted:
- post-window closeout required:
- final operator verdict:

## 4. Minimum allowed authorization

A valid GRANTED decision must keep all of these true:

- target environment: stage / bounded testnet environment only
- invocation surface: POST /trade-gate/testnet-order-intents
- maximum request count: 1
- maximum live funds exposure: 0
- live trading authorized: NO
- go-live: NO-GO
- post-window closeout required: YES

## 5. Current default verdict

- operator authorization filled: NO
- window authorization granted: NO
- real external request authorized now: NO
- canary execution may start now: NO
- go-live: NO-GO
- live trading: NO-GO
- current blocker: OPERATOR_WINDOW_REOPEN_AUTHORIZATION_NOT_FILLED

## 6. Explicit non-claims

- This document does not send a real external request.
- This document does not authorize canary execution.
- This document does not authorize go-live.
- This document does not authorize live trading.

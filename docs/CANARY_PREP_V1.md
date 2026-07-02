# Canary Prep V1

## 1. Purpose

- prepare the future canary step after simulator ACCEPTED / REJECTED / FAILED evidence review
- no canary authorization
- no canary execution
- no simulator request execution
- no real external exchange request

This document is preparation only. It does not authorize canary, live trading, go-live, real exchange requests, or additional simulator requests.

## 2. Current Mainline State

- main HEAD reviewed: `079205f8f1250c1c3d21b879a19c22106951c362`
- post FAILED send mainline review merged: YES
- simulator ACCEPTED evidence reviewed: YES
- simulator REJECTED evidence reviewed: YES
- simulator FAILED evidence reviewed: YES
- duplicate simulator request found: NO
- second FAILED request found: NO
- real external exchange request found: NO
- canary authorization granted: NO
- canary executed: NO
- live trading: NO-GO
- go-live: NO-GO

## 3. Canary Prep Boundary

- this document is prep only
- canary authorization is NOT granted
- canary execution is NOT allowed in this task
- live trading remains NO-GO
- go-live remains NO-GO
- runtime behavior is unchanged
- credentials are unchanged
- backend/worker/risk/deploy are unchanged

## 4. Future Canary Preflight Requirements

Before any future canary authorization or execution task, the following must be verified:

- workspace guard PASS
- local branch is `main`
- local main synced with origin
- git status clean
- simulator tests PASS
- hardened one-shot guardrail PASS
- go-live rules PASS
- local box baseline PASS
- kill switch state explicitly checked
- worker heartbeat explicitly checked
- Telegram / alerting state explicitly checked if canary requires notification
- no pending unexpected commands
- no unresolved simulator evidence gap
- no existing canary request in progress

## 5. Future Canary Execution Boundary

Any future canary execution requires a separate explicit operator authorization after this prep is merged and baseline is clean.

- exactly one canary request only
- bounded notional only
- explicit operator authorization required
- no live trading
- no go-live
- no retry if evidence is incomplete
- no second request without new authorization
- no runtime/env/secrets changes inside the execution task
- no backend/worker/risk/deploy changes inside the execution task

## 6. Expected Future Canary Evidence

The future canary closeout must record:

- command_id
- idempotency key
- request timestamp
- execution mode
- event chain
- final status
- external request status if applicable
- external_order_id presence or absence based on actual result
- duplicate request sent: NO
- canary request count
- kill switch state at execution
- worker heartbeat / processing evidence
- alerting evidence if notification is required
- live trading remains NO-GO
- go-live remains NO-GO

## 7. Stop Conditions For Future Canary

- workspace guard fails
- git status is not clean
- main is not synced
- validation fails
- kill switch state cannot be verified
- worker heartbeat cannot be verified
- alerting readiness cannot be verified when required
- unexpected pending command exists
- operator authorization is missing
- more than one canary request would be sent
- live trading path would be touched
- go-live path would be touched

## 8. Next Safe Status

- `READY_FOR_CANARY_PREP_DOC_PR_MERGE`

After this prep is merged and baseline is clean, the next possible status is `READY_FOR_CANARY_AUTHORIZATION_REQUEST`. This prep does not grant that authorization.

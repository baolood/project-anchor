# Alternative Testnet Venue Review V1

## 1. Purpose

Review possible alternative testnet or sandbox access paths after Binance testnet returned `FAILED/http_451`, and recommend the next safe venue/access-path review surface for a future canary prep.

This review is documentation only:

- canary retried in this task: NO
- external request sent in this task: NO
- simulator replay executed in this task: NO
- DB mutation performed in this task: NO
- executor / network / location / proxy / VPN changed: NO
- credentials changed: NO
- runtime / env / secrets changed: NO
- backend / worker / risk / deploy changed: NO

## 2. Current State

- access path decision merged: YES
- source decision: `docs/ACCESS_PATH_DECISION_V1.md`
- Binance testnet canary result remains FAILED/http_451: YES
- same-path Binance retry rejected: YES
- ad hoc VPN/proxy workaround rejected: YES
- external_order_id present: NO
- retry executed: NO
- live trading: NO-GO
- go-live: NO-GO

## 3. Review Criteria

A future alternative venue or access path must satisfy these criteria before any canary prep can become executable:

- official testnet, sandbox, demo, or paper-trading availability
- API order endpoint availability
- region/access compatibility without ad hoc VPN or proxy workaround
- supports bounded market/limit test order equivalent
- clear credential model
- no real-money exposure
- can be integrated without changing core runner semantics
- can preserve exactly-one request evidence
- can preserve idempotency or client-order-id evidence
- can produce a terminal DONE / FAILED result that fits `commands_domain -> domain_command_worker -> DONE / FAILED`

## 4. Candidate Path Comparison

### Binance testnet same path

- status: rejected for now
- reason: current canary returned `FAILED/http_451`
- same-path retry allowed: NO
- ad hoc VPN/proxy bypass allowed: NO

### Approved alternative exchange testnet/sandbox

- status: candidate
- reviewed example access path: Kraken Derivatives REST / official paper-trading path review
- official order endpoint availability: candidate evidence exists for a Derivatives REST `sendorder` endpoint
- client order identity support: candidate evidence exists through `cliOrdId`
- credential model: documented APIKey / Authent authentication for private REST endpoints
- no-real-money posture: must be confirmed in the future venue-specific prep before any execution
- core runner semantics: candidate only if mapped to the existing bounded exactly-one command model without broad executor rewrite
- decision in this task: do not integrate, do not configure credentials, do not send request

### Simulator-only continuation

- status: safe fallback
- benefit: no external request and no venue/access uncertainty
- limitation: lower external evidence value because it does not test a real testnet/sandbox venue

### Ad hoc VPN/proxy workaround

- status: rejected
- reason: turns a known access/location blocker into an uncontrolled network variable
- allowed by this review: NO

## 5. Recommendation

Recommended next path:

- `READY_FOR_APPROVED_ALTERNATIVE_TESTNET_CANARY_PREP`

This recommendation is limited to preparing a future venue-specific canary prep document for an official, non-real-money testnet/sandbox or paper-trading access path. It does not choose final credentials, does not authorize runtime changes, and does not authorize any request.

If the future prep cannot verify non-real-money exposure, region/access compatibility, credential boundaries, and exactly-one evidence preservation, the path must fall back to:

- `READY_FOR_SIMULATOR_ONLY_CONTINUATION`

## 6. Next Allowed Task

The next allowed task is documentation only:

- Alternative venue canary prep doc only
- no credential change
- no external request
- no runtime behavior change
- no executor / network / location / proxy / VPN change
- no canary execution
- separate future authorization required

The future prep must explicitly document the selected venue/access path, exact endpoint family, credential boundary, no-real-money proof, idempotency/client-order-id mapping, expected event chain, stop conditions, and closeout requirements before any execution can be considered.

## 7. Boundary Preserved

- canary retried: NO
- external request sent in this task: NO
- DB mutation performed in this task: NO
- simulator replay executed: NO
- executor / network / location / proxy / VPN changed: NO
- backend / worker / risk / deploy changed: NO
- runtime / env / secrets changed: NO
- credentials changed: NO
- live trading: NO-GO
- go-live: NO-GO

## 8. Next Safe Status

- `READY_FOR_ALTERNATIVE_TESTNET_VENUE_REVIEW_PR_MERGE`

After this review is merged and baseline is clean, the next possible status is `READY_FOR_APPROVED_ALTERNATIVE_TESTNET_CANARY_PREP`. This review does not authorize canary retry, external requests, go-live, or live trading.

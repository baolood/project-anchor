# Project Anchor Operations Readiness Snapshot

Generated at: `2026-07-22T01:30:03Z`

## Overall

- overall status: WARN
- go-live verdict: NO-GO
- live trading allowed: False

## Health

- backend: PASS
- worker: PASS
- worker heartbeat at: `2026-07-22T01:29:40.574018+00:00`
- kill switch enabled: False
- kill switch source: `none`

## Latest Controlled Request

- command id: `order-a06eed8f-cd60-4a4f-b3e9-84c540b98e6f`
- status: DONE
- external status: FILLED
- external order id present: True
- executed at: `2026-07-18T15:39:27.590704+00:00`
- event chain: PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_ACCEPTED -> ACTION_OK -> MARK_DONE

## Latest Canary

- command id: `order-f4fd182a-7a66-4f3c-a69f-f0a212c2c420`
- status: DONE
- external status: FILLED
- external order id present: True
- executed at: `2026-07-19T05:55:03.323572+00:00`
- event chain: PICKED -> POLICY_ALLOW -> KILL_SWITCH_CHECKED -> TESTNET_EXECUTOR_REQUESTED -> TESTNET_EXECUTOR_ACCEPTED -> ACTION_OK -> MARK_DONE

## Production Execution Readiness

- result: BLOCKED

## Production Execution Authorization Dry Gate

- result: PASS
- authorized to execute: false
- readiness checks: 4/4
- execution gates blocking: 5/5

## Production No-Send Execution Drill

- result: PASS
- no-send path verified: true
- authorized to execute: false

## Production Unsigned Canonical Payload Dry Run

- result: PASS
- unsigned canonical payload generated: true
- sendable: false

## Production Signing Interface Dry Run

- result: PASS
- signing interface shape valid: true
- missing secret fail-closed: true
- real signing executed: false
- Authorization header generated: false
- signed payload sendable: false

## Production HTTP Request Interface Dry Run

- result: PASS
- request envelope shape valid: true
- missing Authorization fail-closed: true
- HTTP/network executed: false
- request sent: false

## Production Pre-Send Readiness Aggregation

- result: PASS
- evidence chain complete: true
- request send authorized: false
- go-live allowed: false
- live trading allowed: false
- next gate: READY_FOR_EXPLICIT_PRODUCTION_REQUEST_SEND_AUTHORIZATION_DECISION

## Production Request Send Window Plan

- result: PASS
- plan valid: true
- send authorized: false
- execution allowed by this plan: false
- planned idempotency key template: `production:ops_manual:BTCUSDT:BUY:4:first-bounded-production-request:v1`
- window expires at: `2026-07-21T11:16:12Z`
- next gate: WAITING_FOR_EXPLICIT_EXACTLY_ONE_PRODUCTION_REQUEST_SEND_AUTHORIZATION

## Production Send Entrypoint Fail-Closed

- result: PASS
- surface: `POST /trade-gate/production-order-intents`
- entrypoint present: true
- send authorized: false
- execution gate authorized: false
- command creation candidate: true
- command type: `PRODUCTION_ORDER_INTENT`
- non-executable persistence status: `CREATED_NOT_EXECUTABLE`
- worker executable: false
- command created: false
- production request sent: false

### Production Gates

- go_live: NO
- live_trading: NO
- production_credential_access: NO
- production_http_network: NO
- production_signing: NO

### Production Blockers

- production credential access not authorized
- production signing not authorized
- production HTTP/network not authorized
- go-live not authorized
- live trading not authorized

## Go-Live Blocking Gates

- production credential access not authorized
- production signing not approved
- production HTTP/network execution not approved
- rollback and stop conditions not approved for go-live
- monitoring window not approved for go-live
- go-live authorization not granted
- live trading authorization not granted

## Boundary

- secret read: NO
- new external request sent: NO
- canary rerun: NO
- runtime modified: NO
- go-live: NO-GO
- live trading: NO-GO

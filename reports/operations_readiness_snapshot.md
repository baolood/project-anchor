# Project Anchor Operations Readiness Snapshot

Generated at: `2026-07-19T15:07:18Z`

## Overall

- overall status: WARN
- go-live verdict: NO-GO
- live trading allowed: False

## Health

- backend: PASS
- worker: PASS
- worker heartbeat at: `2026-07-19T15:07:16.483032+00:00`
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

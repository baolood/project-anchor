# Project Anchor Operations Readiness Snapshot

Generated at: `2026-07-19T08:54:09Z`

## Overall

- overall status: WARN
- go-live verdict: NO-GO
- live trading allowed: False

## Health

- backend: PASS
- worker: PASS
- worker heartbeat at: `2026-07-19T08:54:04.195756+00:00`
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

## Go-Live Blocking Gates

- production market selection not approved
- production credential provisioning not approved
- production signing not approved
- production HTTP/network execution not approved
- production risk limit values not operator-filled
- rollback and stop conditions not approved for go-live
- monitoring window not approved for go-live
- live trading authorization not granted

## Boundary

- secret read: NO
- new external request sent: NO
- canary rerun: NO
- runtime modified: NO
- go-live: NO-GO
- live trading: NO-GO

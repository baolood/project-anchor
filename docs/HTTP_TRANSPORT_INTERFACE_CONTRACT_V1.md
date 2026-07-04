# HTTP Transport Interface Contract V1

## Purpose

Define a local-only transport interface contract for the alternative testnet
HTTP client. This contract models transport input and output shapes only. It
does not import a real HTTP library, open sockets, read credentials, read
env/config, add signing, register runtime paths, execute canary, or send any
external request.

## Current State

- main HEAD before slice: `b5d729d Merge pull request #191 from baolood/codex/http-client-signing-transport-gap-review`
- HTTP request builder contract merged: YES
- signing / transport gap review merged: YES
- request builder remains local-only: YES
- real HTTP library imported: NO
- socket/network behavior enabled: NO
- credentials read: NO
- env/config read: NO
- Authorization / signature implementation added: NO
- runtime path enabled: NO
- external request sent: NO

## Transport Input Contract

- deterministic transport input shape added: YES
- input is derived from local request builder output: YES
- method preserved: YES
- path preserved: YES
- body preserved: YES
- idempotency_key preserved: YES
- venue preserved: YES
- execution_mode preserved: YES
- client_order_ref preserved: YES
- external_order_id before upstream response: NO
- network_sent before execution: NO

## Transport Output Contract

- deterministic transport output shape added: YES
- accepted response shape covered: YES
- rejected response shape covered: YES
- transport-not-executed shape covered: YES
- accepted output may carry external_order_id only when supplied as upstream response evidence: YES
- rejected output external_order_id present: NO
- not-executed output external_order_id present: NO
- network_sent remains false in this no-network contract: YES
- failure_family / failure_reason explicit for non-accepted outputs: YES

## Boundary Preserved

- real HTTP library imported: NO
- socket/network behavior added: NO
- credentials read: NO
- env/config read added: NO
- Authorization/signature implementation added: NO
- runner / worker / risk modified: NO
- runtime path enabled: NO
- external request sent: NO
- canary retried: NO
- live trading: NO-GO
- go-live: NO-GO

## Recommended Next Path

Before any real HTTP transport implementation, close out this contract and
review whether the next safe slice should be a no-network transport closeout
review or an even narrower response parser contract.

- recommended next path: `READY_FOR_HTTP_TRANSPORT_INTERFACE_CONTRACT_PR_MERGE`
- implementation enabled by this slice: NO
- external request authorized by this slice: NO
- canary authorized by this slice: NO

## Final State

- transport interface contract added: YES
- network behavior enabled: NO
- credentials changed: NO
- external request sent: NO
- live trading: NO-GO
- go-live: NO-GO
- next safe status: `READY_FOR_HTTP_TRANSPORT_INTERFACE_CONTRACT_PR_MERGE`

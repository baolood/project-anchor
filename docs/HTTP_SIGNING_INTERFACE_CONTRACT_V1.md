# HTTP Signing Interface Contract V1

## Purpose

Define a local-only signing interface contract for the alternative testnet HTTP
client. This contract models unsigned request, signed request, and
signing-not-executed shapes only. It does not implement a real signing
algorithm, read credentials, read env/config, import HTTP libraries, open
sockets, register runtime paths, execute canary, or send any external request.

## Current State

- main HEAD before slice: `130f46c Merge pull request #192 from baolood/codex/http-transport-interface-contract-slice`
- HTTP request builder contract merged: YES
- HTTP transport interface contract merged: YES
- signing / transport gap review merged: YES
- real HTTP library imported: NO
- socket/network behavior enabled: NO
- credentials read: NO
- env/config read: NO
- real Authorization/signature algorithm added: NO
- runtime path enabled: NO
- external request sent: NO

## Signing Input Contract

- deterministic signing input shape added: YES
- signing input is derived from transport input: YES
- method preserved: YES
- path preserved: YES
- body preserved: YES
- idempotency_key preserved: YES
- venue preserved: YES
- execution_mode preserved: YES
- client_order_ref preserved: YES
- signing material must be explicit input: YES
- env/config lookup for signing material: NO
- credential lookup for signing material: NO

## Signing Output Contract

- deterministic signing output shape added: YES
- unsigned request shape covered: YES
- signed request shape covered: YES
- signing-not-executed shape covered: YES
- Authorization/signature values may only come from explicit mock material: YES
- real Authorization/signature algorithm added: NO
- request body preserved through signing: YES
- request path preserved through signing: YES
- external_order_id created by signing: NO
- network_sent created by signing: NO
- failure_family / failure_reason explicit for not-executed output: YES

## Boundary Preserved

- real HTTP library imported: NO
- socket/network behavior added: NO
- credentials read: NO
- env/config read added: NO
- real Authorization/signature algorithm added: NO
- runner / worker / risk modified: NO
- runtime path enabled: NO
- external request sent: NO
- canary retried: NO
- live trading: NO-GO
- go-live: NO-GO

## Recommended Next Path

Before any real signing implementation, close out this contract and review the
remaining gap between mock signing material and credential custody. No runtime
credential access or external request should be authorized by this contract.

- recommended next path: `READY_FOR_HTTP_SIGNING_INTERFACE_CONTRACT_PR_MERGE`
- real signing enabled by this slice: NO
- credential access authorized by this slice: NO
- external request authorized by this slice: NO
- canary authorized by this slice: NO

## Final State

- signing interface contract added: YES
- real signing enabled: NO
- network behavior enabled: NO
- credentials changed: NO
- external request sent: NO
- live trading: NO-GO
- go-live: NO-GO
- next safe status: `READY_FOR_HTTP_SIGNING_INTERFACE_CONTRACT_PR_MERGE`

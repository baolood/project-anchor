# HTTP Client Signing and Transport Gap Review V1

## Purpose

Review the current local-only HTTP request builder contract and document the
remaining signing and transport gaps before any real HTTP implementation. This
review does not implement signing, add Authorization headers, load credentials,
read env/config, enable runtime paths, execute canary, or send any external
request.

## Current State

- main HEAD before review: `f49d7bf Merge pull request #190 from baolood/codex/http-request-builder-contract-slice`
- HTTP request builder contract merged: YES
- local deterministic request object exists: YES
- method / path / body shape exists: YES
- idempotency_key preserved: YES
- venue preserved: YES
- execution_mode preserved: YES
- symbol / side / notional preserved: YES
- client_order_ref generated locally: YES
- external_order_id created by request builder: NO
- network_sent implied by request builder: NO
- HTTP client tests: PASS, 21 tests
- adapter tests: PASS, 23 tests
- simulator tests: PASS, 5 tests

## Signing Gap Review

- signing requirements documented: YES
- signing implementation present: NO
- Authorization header present: NO
- signature field present: NO
- API key field present: NO
- API secret field present: NO
- token field present: NO
- credential source selected: NO
- credential loading authorized: NO

Future signing work must be separately authorized and must remain blocked until
credential custody, redaction, and runtime boundary reviews are complete.

## Transport Gap Review

- transport requirements documented: YES
- real HTTP library imported: NO
- socket/network behavior present: NO
- full production URL present: NO
- live endpoint present: NO
- timeout policy implemented: NO
- retry policy implemented: NO
- response parser for real upstream payload present: NO
- transport execution authorized: NO

Future transport work must not imply execution. A transport contract may only be
introduced after a separate no-network transport-interface boundary is reviewed.

## Evidence Rules Preserved

- idempotency preservation requirement documented: YES
- no external_order_id before response rule preserved: YES
- network_sent=false until transport execution rule preserved: YES
- no retry without explicit authorization rule preserved: YES
- no canary without explicit authorization rule preserved: YES
- commands_domain -> domain_command_worker -> DONE / FAILED remains the active evidence chain: YES

## Unsafe Next Steps Rejected

- add requests/httpx/aiohttp now: REJECTED
- add socket/network call now: REJECTED
- add Authorization header now: REJECTED
- add signature implementation now: REJECTED
- read env/config now: REJECTED
- load credentials now: REJECTED
- runner / worker / risk integration now: REJECTED
- runtime path enablement now: REJECTED
- external request now: REJECTED
- canary retry now: REJECTED
- go-live or live trading now: REJECTED

## Recommended Next Slice

The next safe slice should remain no-network and should only define the
transport interface contract as inert data and failure semantics. It must not
import a real HTTP library, read credentials, add signing, or register runtime
execution.

- recommended next path: `READY_FOR_HTTP_TRANSPORT_INTERFACE_CONTRACT_SLICE`
- next slice type: no-network transport interface contract only
- signing implementation in next slice: NO
- credentials in next slice: NO
- env/config loading in next slice: NO
- real HTTP library in next slice: NO
- network call in next slice: NO
- runtime integration in next slice: NO
- external request in next slice: NO
- canary authorization in next slice: NO

## Final State

- signing/transport gap review added: YES
- implementation enabled: NO
- network behavior enabled: NO
- credentials changed: NO
- external request sent: NO
- live trading: NO-GO
- go-live: NO-GO
- next safe status: `READY_FOR_HTTP_CLIENT_SIGNING_TRANSPORT_GAP_REVIEW_PR_MERGE`

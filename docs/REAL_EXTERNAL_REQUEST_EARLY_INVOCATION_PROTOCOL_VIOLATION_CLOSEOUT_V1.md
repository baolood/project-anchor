# Real External Request Early Invocation Protocol Violation Closeout V1

## Result

- execution result: PROTOCOL_VIOLATION
- blocker: POST_SENT_BEFORE_WINDOW_OPEN
- valid window execution: NO
- real external request sent to backend endpoint: YES
- external exchange request started: false
- external order id present: false
- command id: order-54b2b26d-b958-44e6-bf26-1830c88aba43
- command final status: FAILED
- failure family: TESTNET_CREDENTIALS_MISSING
- worker picked command: YES
- worker stopped for reconciliation: YES
- no retry: YES
- no second request: YES
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO
- worker restore authorized by this closeout: NO

## Time Facts

- authorized window start: 2026-06-05T16:51:18+08:00
- authorized window end: 2026-06-05T17:06:18+08:00
- actual POST time approx: 2026-06-05T16:45:19+08:00
- time guard result observed: WINDOW_NOT_OPEN_YET

## Safety Classification

The POST reached the backend endpoint before the authorized window opened.

The worker processed the command and failed it at credential gate:

- gate: credential_presence
- canonical path: ORDER:testnet
- external_request_started: false
- external_order_id_present: false

Therefore no external exchange order was created and no live trading exposure was created.

## Evidence

Host-side evidence location:

/root/project-anchor/artifacts/early-invocation-reconciliation/20260605T165009+0800

Evidence files:

- early_invocation_reconciliation_summary.txt
- worker_tail.txt
- backend_tail.txt

## Root Cause

The shell execution block did not stop after the Python time guard returned WINDOW_NOT_OPEN_YET.

Future execution must use strict stop behavior before POST.

## Next Required Action

- keep worker stopped until closeout is merged or explicitly accepted
- create hardened one-shot execution script with strict time guard enforcement
- do not retry
- do not send a second request

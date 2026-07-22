# Final Production Send Runner

Generated at: `2026-07-22T09:04:07Z`

## Result

- result: PASS
- default failure code: PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED
- no execute failure code: PRODUCTION_SEND_EXECUTION_NOT_AUTHORIZED
- fake transport terminal type: PRODUCTION_HTTP_RESPONSE
- fake transport external status: FILLED
- fake transport external order id present: true
- fake transport called once: true

## Checks

- default_credential_read_fails_closed: PASS
- fixture_credentials_still_require_execute: PASS
- fixture_fake_transport_path_parses_response: PASS
- redaction_preserved: PASS

## Boundary

- real credential file read: NO
- fixture credential file read: YES
- secret value disclosed: NO
- secret length disclosed: NO
- secret prefix/suffix disclosed: NO
- secret hash disclosed: NO
- production signing with real secret: NO
- Authorization header value disclosed: NO
- DNS lookup performed: NO
- socket opened: NO
- production HTTP/network executed: NO
- production request sent: NO
- canary rerun: NO
- go-live: NO-GO
- live trading: NO-GO

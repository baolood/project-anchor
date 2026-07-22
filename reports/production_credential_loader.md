# Production Credential Loader

Generated at: `2026-07-22T08:55:33Z`

## Result

- result: PASS
- loader default code: PRODUCTION_CREDENTIAL_READ_NOT_AUTHORIZED
- loader fixture code: PRODUCTION_CREDENTIALS_LOADED

## Redacted Shape

- loaded: True
- base_url_present: True
- api_key_present: True
- api_secret_present: True
- key_id_present: True
- field_status: {'PRODUCTION_EXCHANGE_BASE_URL': 'PRESENT_VALID', 'PRODUCTION_EXCHANGE_API_KEY': 'PRESENT_VALID', 'PRODUCTION_EXCHANGE_API_SECRET': 'PRESENT_VALID', 'PRODUCTION_EXCHANGE_KEY_ID': 'PRESENT_VALID'}
- secret_value_disclosed: False

## Checks

- default_read_fails_closed: PASS
- authorized_fixture_loads: PASS
- redacted_shape_valid: PASS
- secret_values_not_rendered: PASS

## Boundary

- real credential file read: NO
- fixture credential file read: YES
- secret value disclosed: NO
- secret length disclosed: NO
- secret prefix/suffix disclosed: NO
- secret hash disclosed: NO
- production signing executed: NO
- Authorization header generated: NO
- DNS lookup performed: NO
- socket opened: NO
- production HTTP/network executed: NO
- production request sent: NO
- canary rerun: NO
- go-live: NO-GO
- live trading: NO-GO

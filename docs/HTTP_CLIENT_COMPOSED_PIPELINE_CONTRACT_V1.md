# HTTP Client Composed Pipeline Contract V1

## Summary

This document records the local-only composed pipeline contract for the approved
alternative testnet HTTP client.

The pipeline composes the existing local contracts:

1. request builder contract
2. signing interface contract
3. transport interface contract

This is not a real HTTP execution path. It does not enable signing, credential
loading, network I/O, runtime registration, canary execution, live trading, or
go-live.

## Current State

- HTTP request builder contract merged: YES
- HTTP transport interface contract merged: YES
- HTTP signing interface contract merged: YES
- real signing enabled: NO
- network behavior enabled: NO
- credentials changed: NO
- env/config read added: NO
- runtime path enabled: NO
- external request sent: NO
- canary retried: NO
- live trading: NO-GO
- go-live: NO-GO

## Contract Added

- composed pipeline contract added: YES
- builder -> signing -> transport shape covered: YES
- build-only shape covered: YES
- signed-not-sent shape covered: YES
- transport-not-executed shape covered: YES
- accepted response shape covered: YES
- rejected response shape covered: YES
- idempotency_key preserved end-to-end: YES
- request body/query preserved end-to-end: YES
- signing creates external_order_id: NO
- signing creates network_sent=true: NO
- transport creates network_sent=true before real execution: NO
- accepted/rejected results come from mock/upstream-like response objects only: YES

## Boundary

- real HTTP library imported: NO
- socket/network behavior added: NO
- credentials read: NO
- env/config read added: NO
- real Authorization/signature algorithm added: NO
- runner modified: NO
- worker modified: NO
- risk modified: NO
- runtime path enabled: NO
- external request sent: NO
- canary retried: NO
- live trading: NO-GO
- go-live: NO-GO

## Evidence Requirements

The composed pipeline must preserve reviewable evidence fields without implying
that a real request happened:

- idempotency_key
- venue
- execution_mode
- method
- path
- client_order_ref
- body
- material_id, only when explicit mock signing material is supplied
- authorization_header_value, only from explicit mock signing material
- signature_value, only from explicit mock signing material
- network_sent=false
- external_order_id absent until an upstream-like accepted response object is
  supplied
- failure_family and failure_reason for rejected or not-executed shapes

## Validation

- HTTP client tests: PASS expected
- adapter tests: PASS expected
- simulator tests: PASS expected
- hardened one-shot guardrail: PASS expected
- go-live rules: PASS expected
- local box baseline: PASS expected
- git diff --check: PASS expected

## Next Safe Status

`READY_FOR_HTTP_CLIENT_COMPOSED_PIPELINE_CONTRACT_PR_MERGE`

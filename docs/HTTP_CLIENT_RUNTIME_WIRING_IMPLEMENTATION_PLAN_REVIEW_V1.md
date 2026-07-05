# HTTP Client Runtime Wiring Implementation Plan Review V1

## Summary

This document reviews the minimal future implementation plan for HTTP client
runtime wiring after the preimplementation guardrail merged.

This is a plan review only. It does not implement runtime wiring, does not
modify runner / worker / risk, does not enable a runtime path, does not read
env/config or credentials, and does not send external requests.

## Current State

- runtime wiring preimplementation guardrail merged: YES
- runtime wiring implemented: NO
- runner modified: NO
- worker modified: NO
- risk modified: NO
- runtime path enabled: NO
- real signing enabled: NO
- network behavior enabled: NO
- credentials changed: NO
- env/config read added: NO
- external request sent: NO
- canary retried: NO
- live trading: NO-GO
- go-live: NO-GO

## Review Result

- runtime wiring implementation plan reviewed: YES
- minimal implementation file list documented: YES
- forbidden file list documented: YES
- runner/worker/risk boundary documented: YES
- runtime path disabled requirement documented: YES
- canary-before-runtime requirements documented: YES
- rollback plan documented: YES
- disabled-state acceptance documented: YES
- no runtime wiring implemented: YES

## Minimal Future Implementation File List

The first future runtime wiring implementation slice may only be considered
after separate authorization. The proposed minimal file list for that future
slice should remain narrow and must be revalidated before execution:

- `anchor-backend/app/actions/alternative_testnet_http_client.py`
- `tests/test_alternative_testnet_http_client.py`
- a dedicated docs closeout or checklist update

Any future proposal that needs runner / worker / risk files must first create a
separate runner/worker boundary review PR. It must not be folded into the first
runtime wiring implementation slice.

## Forbidden File List

The following remain forbidden in this review and should remain forbidden for
the first implementation slice unless a later explicit authorization narrows
and changes the boundary:

- `anchor-backend/app/actions/runner.py`
- `anchor-backend/app/workers/`
- `anchor-backend/worker/`
- `anchor-backend/app/risk/`
- `anchor-backend/app/services/risk_engine.py`
- `anchor-backend/app/system/risk_gate.py`
- deploy files
- env files
- docker / compose files
- migrations
- credential files

## Runner / Worker / Risk Boundary

No runner, worker, or risk path may call the alternative testnet HTTP client in
this review.

Before any future runner / worker / risk integration:

- runner boundary tests must exist
- worker boundary tests must exist
- risk boundary tests must exist
- command lifecycle evidence must remain under commands_domain ->
  domain_command_worker
- disabled-by-default behavior must be locally provable
- no canary or external request may be implied by the integration itself

## Runtime Path Disabled Requirement

Runtime path enablement must remain disabled until a separate implementation PR
is authorized and merged.

Required disabled-state evidence:

- runtime_path_enabled: NO
- network_sent=false before authorized transport execution
- external_order_id absent before upstream-like accepted response
- real_signing_enabled: NO
- network_behavior_enabled: NO
- credentials_changed: NO
- env/config read added: NO
- external_request_sent: NO
- canary_retried: NO

## Canary-Before-Runtime Requirements

Before any future runtime wiring implementation may lead toward canary:

- runtime wiring implementation must be merged separately
- local baseline must pass after merge
- no runner / worker / risk integration may be assumed from HTTP client tests
- a separate canary preflight must be completed
- explicit user authorization must be obtained
- canary remains NOT AUTHORIZED by this review

## Rollback Plan

If a future runtime wiring implementation PR is merged and validation fails:

1. stop immediately
2. do not execute canary
3. do not send external requests
4. identify the runtime wiring merge commit
5. revert that merge commit through a follow-up PR or approved revert flow
6. rerun HTTP client tests, adapter tests, simulator tests, guardrails,
   go-live rules, local box baseline, and `git diff --check`

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

## Next Safe Status

`READY_FOR_HTTP_CLIENT_RUNTIME_WIRING_IMPLEMENTATION_PLAN_REVIEW_PR_MERGE`

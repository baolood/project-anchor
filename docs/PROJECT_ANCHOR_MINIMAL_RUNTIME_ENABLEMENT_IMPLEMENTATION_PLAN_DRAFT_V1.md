# Project Anchor Minimal Runtime Enablement Implementation Plan Draft V1

## Purpose

Draft the minimal runtime enablement implementation plan after PR #266 documentation review, without changing runtime code.

This plan does not authorize implementation.

This plan does not enable runtime.

This plan does not authorize credential/env/config access.

This plan does not authorize signing.

This plan does not authorize HTTP/network.

This plan does not authorize canary or any external request.

## Current Locked State

PROJECT_ANCHOR_MINIMAL_RUNTIME_ENABLEMENT_IMPLEMENTATION_PREP_DOCUMENTATION_REVIEW_MERGED_RUNTIME_DISABLED

Latest main HEAD:

`1ab14ed Merge pull request #266 from baolood/codex/project-anchor-minimal-runtime-enablement-implementation-prep-documentation-review`

## Current Boundary

- runtime enablement authorization granted: NO
- runtime implementation authorization granted: PREP ONLY
- runtime path enabled: NO
- credentials/env/config read: NO
- real signing enabled: NO
- real HTTP/network enabled: NO
- external request sent: NO
- canary executed: NO
- go-live/live trading: NO-GO

## Minimal Implementation Candidate Scope

This draft identifies candidate surfaces only. Runtime candidates are not authorized yet.

Documentation candidate files:

- `docs/PROJECT_ANCHOR_MINIMAL_RUNTIME_ENABLEMENT_IMPLEMENTATION_PLAN_DRAFT_V1.md` - authorized for this draft
- `docs/GO_LIVE_CHECKLIST.md` - candidate for a later separately authorized implementation PR

Runtime or test candidate files for a later implementation PR:

- `anchor-backend/app/actions/alternative_testnet_http_client.py` - runtime candidate, NOT AUTHORIZED YET
- `tests/test_alternative_testnet_http_client.py` - test candidate, NOT AUTHORIZED YET

Explicitly not in scope without separate authorization:

- `anchor-backend/app/actions/runner.py` - NOT AUTHORIZED YET
- worker paths - NOT AUTHORIZED YET
- risk paths - NOT AUTHORIZED YET
- deploy/docker/env/runtime configuration paths - NOT AUTHORIZED YET
- signing or transport implementation paths - NOT AUTHORIZED YET

## Explicit Forbidden Side Effects

The minimal implementation path must preserve these side-effect boundaries unless a later separate authorization explicitly changes them:

- no env/config/credential read
- no signing execution
- no HTTP/network execution
- no socket/network behavior
- no external exchange request
- no canary
- no go-live/live trading
- no worker/runner runtime enablement without separate implementation authorization
- no external_order_id creation before an upstream accepted response in any future real path

## Proposed Implementation Phases

### Phase 1: Disabled-By-Default Wiring Only

- add or refine a disabled-by-default runtime enablement skeleton only after separate implementation authorization
- preserve disabled result shape and negative evidence
- do not execute credentials/env/config reads
- do not execute signing
- do not execute HTTP/network transport
- do not create external_order_id
- do not send external requests

### Phase 2: Local Validation Only

- validate disabled behavior locally
- validate negative evidence remains present
- validate no runner/worker/risk wiring has been introduced unless separately authorized
- validate no env/config/credential read, signing, HTTP/network, external request, or canary behavior exists

### Phase 3: Separate Runtime Enablement Execution Authorization Request

- prepare a separate execution authorization request only after Phase 1 and Phase 2 are complete
- require explicit operator fields before any runtime execution boundary changes
- reject casual continuation language such as continue, go ahead, next step, or similar wording

### Phase 4: Separate Exactly-One Canary Authorization Request

- prepare exactly-one canary authorization only after runtime execution authorization is complete
- require a fresh bounded window, rollback plan, local validation evidence, and operator signoff
- keep go-live/live trading as NO-GO unless separately authorized in a later process

## Future Implementation PR Acceptance Criteria

A future separately authorized implementation PR must satisfy at minimum:

- default runtime disabled: YES
- no credentials read: YES
- no network sent: YES
- no external_order_id created before upstream accepted response: YES
- disabled result shape preserved: YES
- negative evidence preserved: YES
- runtime path enablement remains blocked by default: YES
- signing and transport remain unexecuted while disabled: YES
- all existing guardrails pass: YES
- no canary or external request is performed by the PR: YES

## Validation Commands

Documentation-only plan draft validation:

- `git diff --check`
- `bash scripts/check_checklist_curl_guardrails.sh`
- `bash scripts/check_go_live_rules.sh`
- `bash scripts/check_local_box_baseline.sh`
- PR checks: PASS

Future implementation validation, if later code changes are separately authorized:

- relevant unit tests for changed runtime/test files
- HTTP client disabled-runtime tests
- adapter tests when adapter-facing behavior changes
- simulator tests when simulator-facing behavior changes
- hardened one-shot guardrail when execution surfaces change
- all documentation-only validation commands listed above

## Rollback Method

If this plan draft PR is merged and later needs to be reverted:

```sh
git checkout main
git pull --ff-only origin main
git revert -m 1 <MERGE_COMMIT>
git push origin main
```

If a future implementation commit is separately authorized and later needs rollback:

```sh
git checkout main
git pull --ff-only origin main
git revert <IMPLEMENTATION_COMMIT>
git push origin main
```

If a future feature flag is introduced later:

- disable the feature flag first
- confirm runtime remains disabled
- confirm no external request was sent
- confirm no canary was executed
- run the validation commands before closing rollback

## Required Next State

NEXT_SAFE_STATE=READY_FOR_MINIMAL_RUNTIME_ENABLEMENT_IMPLEMENTATION_PLAN_REVIEW

RUNTIME_REMAINS_DISABLED=YES

External request sent: NO

Canary executed: NO

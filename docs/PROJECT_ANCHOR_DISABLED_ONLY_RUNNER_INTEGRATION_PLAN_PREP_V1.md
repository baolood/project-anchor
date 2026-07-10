# Project Anchor Disabled-Only Runner Integration Plan Prep V1

## Purpose

Prepare a future disabled-only runner integration plan after the runner / worker / risk boundary review has confirmed that runtime HTTP client wiring is not currently present.

This is a plan-prep artifact only. It does not authorize or implement runner wiring, worker wiring, risk wiring, runtime path enablement, credentials/env/config reads, real signing, real HTTP/network transport, external request, canary, go-live, or live trading.

## Baseline

- previous locked state: PROJECT_ANCHOR_RUNNER_WORKER_RISK_BOUNDARY_REVIEW_MERGED_RUNTIME_DISABLED
- previous next safe state: READY_FOR_DISABLED_ONLY_RUNNER_INTEGRATION_PLAN_PREP
- current baseline HEAD: `5e0b71d Merge pull request #277 from baolood/codex/project-anchor-runner-worker-risk-boundary-review`
- runner / worker / risk boundary reviewed: YES
- runner / worker / risk remain unwired: YES
- runtime remains disabled: YES
- external request sent: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

## Plan Prep Scope

The future disabled-only runner integration plan should be limited to a non-executing interface plan. It should describe how a runner-level integration could surface the disabled HTTP client runtime status without allowing execution.

The future plan must preserve these constraints:

- runner integration remains disabled by default
- no worker execution path is activated
- no risk policy path is changed
- no credentials/env/config are read
- no real signing is performed
- no real HTTP/network transport is used
- no external request is sent
- no canary is executed
- command lifecycle authority remains with commands_domain -> domain_command_worker

## Required Future Plan Sections

The future disabled-only runner integration plan should include:

1. exact allowed files for a future implementation proposal
2. exact forbidden files for the proposal
3. proposed runner-facing disabled result shape
4. proof that disabled result generation does not call signing or transport
5. proof that worker and risk behavior remain unchanged
6. rollback plan for any future code change
7. explicit operator authorization requirement before implementation

## Rejected Shortcuts

The following remain rejected:

- implement runner wiring during this prep
- call the HTTP client from runner during this prep
- introduce runtime path enablement flags in runner
- read credentials/env/config
- add real signing
- add real HTTP/network transport
- send an external request
- execute canary
- treat this plan prep as implementation authorization

## Prep Result

DISABLED_ONLY_RUNNER_INTEGRATION_PLAN_PREP_RESULT=PASS

The next safe step is a separate disabled-only runner integration plan artifact. This prep does not authorize implementation or execution.

## Locked Boundary Preserved

- DNS changed: NO
- A/CNAME created: NO
- `45.76.190.109` bound: NO
- TLS requested: NO
- ingress opened: NO
- runner / worker / risk modified: NO
- runner / worker / risk wiring authorized: NO
- credentials/env/config read: NO
- real signing enabled: NO
- real HTTP/network enabled: NO
- runtime path enabled: NO
- external request sent: NO
- canary retried: NO
- canary executed: NO
- go-live: NO-GO
- live trading: NO-GO

## Final State

PROJECT_ANCHOR_DISABLED_ONLY_RUNNER_INTEGRATION_PLAN_PREP_MERGED_RUNTIME_DISABLED

## Next Safe State

NEXT_SAFE_STATE=READY_FOR_DISABLED_ONLY_RUNNER_INTEGRATION_PLAN

RUNTIME_REMAINS_DISABLED=YES

External request sent: NO

Canary executed: NO

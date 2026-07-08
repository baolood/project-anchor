# Project Anchor Workflow Tiering V1

## Purpose

Define three workflow tiers for Project Anchor so low-risk documentation work can move faster without weakening hard safety boundaries for DNS, ingress, runtime enablement, credentials, real signing, real HTTP/network, external request, canary, go-live, or live trading.

This is a docs-only process review. It does not change DNS, nameservers, TLS, ingress, cloud-host binding, runtime behavior, runner/worker/risk code, credentials/env/config access, signing, HTTP transport, external requests, canary, go-live, or live trading.

## Tier A: Low-Risk Workflow

### Applies To

- docs-only changes
- checklist-only changes
- closeout review documents
- status summary documents
- read-only evidence records

### Simplified Required Checks

- git status clean before task: REQUIRED
- allowed files only: REQUIRED
- forbidden files touched: NO
- git diff --check: REQUIRED
- PR checks PASS before merge: REQUIRED
- rollback method recorded: REQUIRED

Low-risk tasks do not need to repeat the full high-risk boundary template in every closeout when the changed files and PR body clearly state that no execution, DNS, credential, network, runtime, or canary behavior changed.

## Tier B: Medium-Risk Workflow

### Applies To

- tests added
- guardrail tests
- disabled skeleton changes
- integration surface changes
- domain/DNS planning documents
- Cloudflare read-only evidence documents

### Required Checks

- workspace guard: REQUIRED
- allowed files: REQUIRED
- forbidden files touched: NO
- targeted validation: REQUIRED
- PR checks PASS before merge: REQUIRED
- closeout: REQUIRED
- rollback method: REQUIRED

Medium-risk tasks keep the current structured review style because they either add enforceable tests or move closer to integration, domain, DNS, or runtime boundaries.

## Tier C: High-Risk Workflow

### Applies To

- DNS changes
- nameserver changes
- TLS certificate request
- SSL/TLS mode change
- ingress opening
- cloud host binding
- runner/worker/risk wiring
- credentials/env/config read
- real signing implementation
- real HTTP/network implementation
- runtime path enablement
- external request
- canary
- go-live
- live trading

### Required Controls

- separate explicit authorization: REQUIRED
- exact allowed scope: REQUIRED
- exact forbidden scope: REQUIRED
- preflight: REQUIRED
- execution window when applicable: REQUIRED
- exactly-one guardrail when applicable: REQUIRED
- rollback plan: REQUIRED
- closeout: REQUIRED
- PR checks PASS before merge: REQUIRED
- human confirmation for execution boundary: REQUIRED

High-risk tasks must not be simplified. They remain blocked unless the operator provides explicit authorization for that specific boundary.

## Cross-Tier Hard Boundaries

These boundaries are never relaxed by workflow tiering:

- DNS changes require separate authorization: YES
- nameserver changes require separate authorization: YES
- TLS requests require separate authorization: YES
- ingress opening requires separate authorization: YES
- runtime enablement requires separate authorization: YES
- runner/worker/risk wiring requires separate authorization: YES
- credentials/env/config read requires separate authorization: YES
- real signing requires separate authorization: YES
- real HTTP/network requires separate authorization: YES
- external request requires separate authorization: YES
- canary requires separate authorization: YES
- go-live remains NO-GO until separately authorized: YES
- live trading remains NO-GO until separately authorized: YES

## Intended Effect

The low-risk path should reduce repeated boilerplate for docs-only and review-only work. The medium-risk path preserves the current evidence model for tests, guardrails, disabled skeletons, integration surfaces, and DNS planning. The high-risk path remains fully gated.

This tiering changes process documentation only. It does not authorize runtime enablement or any external-world change.

## Next Safe Status

READY_FOR_PROJECT_ANCHOR_WORKFLOW_TIERING_PR_MERGE

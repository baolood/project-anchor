# HTTP Client Runtime Enablement Domain Usage Decision V1

## Purpose

Record how the already-purchased domain should be treated while HTTP client runtime enablement remains disabled.

This is a docs-only decision. It does not change DNS, bind a domain to the cloud host, open ingress, enable runtime execution, send an external request, or authorize canary.

## Current Domain Posture

- domain purchased: YES
- exact domain name recorded in this artifact: NO
- exact domain name required before DNS work: YES
- domain currently treated as idle reserved asset: YES
- DNS changed in this task: NO
- cloud host bound to domain in this task: NO
- public ingress opened in this task: NO
- runtime path enabled in this task: NO
- external request sent in this task: NO
- canary executed in this task: NO

The domain should not remain conceptually vague forever, but the next safe move is to define its intended use before any DNS or ingress mutation.

## Bounded Future Use

The first acceptable domain-backed use should remain operator/reviewer oriented:

- future `ops.<domain>`: operator-only review and status entry
- future `review.<domain>`: audit/read-only review entry
- bare domain: either unused or redirected to the same bounded review posture

The first domain-backed surface must not be:

- a public product homepage
- a raw backend API entrypoint
- a trading/execution endpoint
- a runner / worker / risk control surface
- a credential or environment configuration surface
- a signal that live trading or go-live is approved

## Required Before DNS Binding

Before any DNS binding task may begin, all of the following must be documented or freshly verified:

- exact domain name recorded: OPEN
- DNS provider/control ownership confirmed: OPEN
- target hostname plan confirmed: OPEN
- TLS plan documented: OPEN
- operator/reviewer auth boundary documented: OPEN
- ingress surface decision documented: OPEN
- raw backend exposure remains forbidden: OPEN
- cloud host freshly verified against current main: OPEN
- cloud host rollback and DNS retreat plan documented: OPEN
- runtime path remains disabled until separate authorization: OPEN
- external request authorization remains separate: OPEN
- canary authorization remains separate: OPEN

## Cloud Host Relationship

- known future host target exists: YES
- target host provider/role: `Vultr Project Anchor stage host`
- target host public IP: `45.76.190.109`
- target host hostname: `vultr`
- target host repo path: `/root/project-anchor`
- historical host alignment exists: YES
- historical host alignment treated as current-main proof: NO
- domain binding to this host authorized by this artifact: NO

The domain and cloud host are related but separately gated. A purchased domain does not authorize binding DNS to the Vultr host, and a known Vultr host does not authorize public ingress.

## Explicitly Forbidden In This Slice

- DNS record changes
- nameserver changes
- Cloudflare/proxy setup
- A/CNAME binding to the cloud host
- reverse proxy or ingress changes
- public raw backend exposure
- runtime enablement
- runner / worker / risk wiring
- credential or env/config reading
- real signing implementation
- real HTTP transport implementation
- external request
- canary
- go-live
- live trading

## Boundary Preserved

- real HTTP library imported: NO
- socket/network behavior added: NO
- credentials read: NO
- env/config read added: NO
- real Authorization/signature algorithm added: NO
- runner/worker/risk modified: NO
- runtime path enabled: NO
- DNS changed: NO
- cloud host changed: NO
- external request sent: NO
- canary retried: NO
- go-live authorized: NO
- live trading authorized: NO

## Validation Reviewed

- HTTP client tests: PASS, 81 tests
- adapter tests: PASS, 23 tests
- simulator tests: PASS, 5 tests
- hardened one-shot guardrail: PASS
- go-live rules: PASS
- local box baseline: PASS
- git diff --check: PASS
- checklist-curl-guardrails: PASS
- latest check before merge: PASS

## Next Safe Status

READY_FOR_HTTP_CLIENT_RUNTIME_ENABLEMENT_DOMAIN_USAGE_DECISION_PR_MERGE

# HTTP Client Runtime Enablement Domain DNS Auth Ingress Prep V1

## Purpose

Prepare the domain DNS/auth/ingress evidence checklist for the already-purchased domain while HTTP client runtime enablement remains disabled.

This is a docs-only preparation slice. It does not change DNS, bind the domain to the cloud host, configure TLS, implement auth, open ingress, enable runtime execution, send an external request, or authorize canary.

## Starting Point

- domain usage decision merged: YES
- domain purchase treated as idle reserved asset: YES
- exact domain name recorded in this prep: NO
- DNS work authorized by this prep: NO
- auth implementation authorized by this prep: NO
- ingress implementation authorized by this prep: NO
- cloud host binding authorized by this prep: NO
- runtime enablement authorized by this prep: NO

## Prep Decision

The domain may remain reserved, but the next safe activity is evidence preparation only.

The project is not ready to point DNS at the cloud host until all required DNS, TLS, auth, ingress, rollback, and cloud-host verification inputs are recorded and reviewed in a separate task.

## Required DNS Evidence Before Any DNS Change

- exact domain name recorded: OPEN
- registrar/account owner confirmed without secret disclosure: OPEN
- DNS provider selected or confirmed: OPEN
- DNS zone control confirmed without changing records: OPEN
- intended records documented: OPEN
- record TTL strategy documented: OPEN
- rollback/retreat DNS plan documented: OPEN
- no nameserver change required for this prep: YES
- no A/CNAME record created in this prep: YES

## Required Auth Evidence Before Any Public Review Surface

- first surface remains operator/reviewer-only: OPEN
- anonymous public access forbidden: YES
- raw backend exposure forbidden: YES
- runner/worker/risk controls forbidden: YES
- credential/env/config views forbidden: YES
- auth boundary selected or explicitly deferred: OPEN
- operator identity expectations documented: OPEN
- failure behavior for unauthenticated access documented: OPEN

## Required TLS Evidence Before Any Domain Binding

- TLS provider/mechanism documented: OPEN
- certificate issuance path documented: OPEN
- renewal responsibility documented: OPEN
- failure/expiry retreat behavior documented: OPEN
- no certificate requested in this prep: YES
- no reverse proxy configured in this prep: YES

## Required Ingress Evidence Before Any Host Binding

- exact intended surface documented: OPEN
- recommended future surface remains `ops.<domain>` / `review.<domain>`: YES
- bare domain behavior documented before use: OPEN
- `/ops` exposure remains operator/reviewer-only: YES
- `/commands` exposure remains operator/reviewer-only: YES
- `/commands/[id]` exposure remains operator/reviewer-only: YES
- raw backend API exposure remains forbidden: YES
- ingress rollout task remains separate: YES
- ingress rollback task remains separate: YES

## Required Cloud-Host Evidence Before Binding

- target host remains known: YES
- target host provider/role: `Vultr Project Anchor stage host`
- target host public IP: `45.76.190.109`
- target host hostname: `vultr`
- target host repo path: `/root/project-anchor`
- cloud host freshly verified against current main in this prep: NO
- historical host alignment treated as current-main proof: NO
- host deploy/rebuild/restart performed in this prep: NO
- host credentials/env inspected in this prep: NO
- host external request sent in this prep: NO
- host canary executed in this prep: NO
- fresh read-only cloud-host verification required before binding: YES

## Explicitly Not Authorized

- DNS record changes
- nameserver changes
- Cloudflare/proxy setup
- TLS certificate request
- reverse proxy configuration
- A/CNAME binding to `45.76.190.109`
- public raw backend access
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
- TLS changed: NO
- auth implemented: NO
- ingress opened: NO
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

READY_FOR_HTTP_CLIENT_RUNTIME_ENABLEMENT_DOMAIN_DNS_AUTH_INGRESS_PREP_PR_MERGE

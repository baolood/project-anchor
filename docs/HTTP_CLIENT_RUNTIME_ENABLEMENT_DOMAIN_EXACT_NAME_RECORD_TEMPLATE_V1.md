# HTTP Client Runtime Enablement Domain Exact Name Record Template V1

## Purpose

Define the exact domain-name record template required before any DNS/auth/TLS/ingress work can begin.

This is a docs-only template. It does not record the real domain value yet, change DNS, bind the domain to the cloud host, configure TLS, implement auth, open ingress, enable runtime execution, send an external request, or authorize canary.

## Current Status

- domain purchased: YES
- exact domain value provided in this task: NO
- exact domain recorded by this artifact: NO
- exact domain record template added: YES
- DNS/auth/TLS/ingress prep merged: YES
- DNS work authorized by this template: NO
- cloud host binding authorized by this template: NO
- runtime enablement authorized by this template: NO

## Required Operator-Filled Fields

Before a future DNS or ingress task may begin, an operator must fill these fields in a separate reviewed artifact:

```text
DOMAIN_EXACT_NAME=<operator fills exact registered domain>
REGISTRAR_NAME=<operator fills registrar, no credentials>
DNS_PROVIDER_NAME=<operator fills DNS provider, no credentials>
DNS_ZONE_CONTROL_CONFIRMED=yes/no
NAMESERVER_CHANGE_REQUIRED=yes/no
INTENDED_FIRST_HOSTNAME=ops.<domain> / review.<domain> / other-reviewed-value
BARE_DOMAIN_BEHAVIOR=unused / redirect-to-review-entry / other-reviewed-value
TLS_PLAN=<provider/mechanism, no secrets>
AUTH_BOUNDARY=<operator/reviewer-only mechanism or deferred decision>
INGRESS_ROLLBACK_PLAN=<how to retreat DNS/ingress safely>
```

The real domain name must be recorded exactly as purchased. Do not abbreviate it, infer it from prior conversation, or replace it with a placeholder in a rollout task.

## What Counts As Evidence

Acceptable evidence:

- exact domain name typed by the operator
- registrar name without login details or secrets
- DNS provider name without API token or account secret
- zone control confirmed as a status only
- intended hostname recorded as a plan, not created in DNS
- TLS/auth/rollback plans written as docs, not implemented

Unacceptable evidence:

- screenshots or values containing secrets
- DNS provider API tokens
- registrar credentials
- live nameserver mutation
- A/CNAME records created during the record step
- cloud host reverse proxy changes
- public ingress proof obtained by opening ingress

## Record Acceptance Gate

The future exact-name record may be accepted only if all of these are true:

- exact domain name is present: YES
- registrar/provider names are present without secrets: YES
- DNS zone control is confirmed without mutation: YES
- intended first hostname is review/operator bounded: YES
- bare domain behavior is explicit: YES
- TLS plan is documented without implementation: YES
- auth boundary remains non-public by default: YES
- ingress rollback plan is documented: YES
- DNS remains unchanged: YES
- cloud host remains unchanged: YES
- runtime path remains disabled: YES
- external request/canary remain absent: YES

## Still Open After This Template

- exact domain name recorded: OPEN
- DNS provider/control evidence recorded: OPEN
- intended first hostname finalized: OPEN
- bare domain behavior finalized: OPEN
- TLS plan finalized: OPEN
- auth boundary finalized: OPEN
- ingress rollback plan finalized: OPEN
- fresh cloud-host verification before binding: OPEN
- separate DNS implementation authorization: OPEN
- separate ingress implementation authorization: OPEN

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

READY_FOR_HTTP_CLIENT_RUNTIME_ENABLEMENT_DOMAIN_EXACT_NAME_RECORD_TEMPLATE_PR_MERGE

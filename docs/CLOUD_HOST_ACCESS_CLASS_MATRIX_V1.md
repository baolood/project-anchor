# Cloud host access class matrix V1

**Status:** access classification only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** classify the current Project Anchor cloud-host-related access paths into stable access classes so future ingress, proxy, and operator decisions are made against one shared matrix instead of ad hoc judgment.

This matrix does not approve public exposure, domain setup, or live trading.

## 1. Access classes

The current cloud-host-related access classes should be interpreted as:

```text
local-only
operator-only
future-public
forbidden-for-now
```

Meaning:

- `local-only`: should exist only on the host itself or inside tightly local engineering/runtime boundaries
- `operator-only`: may be used by a trusted operator under controlled review procedures, but is not general user ingress
- `future-public`: may eventually become part of a productized entry path, but should not be opened yet
- `forbidden-for-now`: should not be reachable or usable in the current stage because opening it now would outrun the project’s proven safety posture

## 2. Matrix

| Access path / surface | Current class | Why this class now | Required posture before reclassification |
|---|---|---|---|
| Cloud host shell / SSH login | operator-only | required for bounded engineering, deploy, rollback, and incident handling; not a product feature | keep limited to trusted operators with explicit review responsibility |
| Local container / compose service wiring on host | local-only | internal runtime boundary only; not an ingress path | keep non-public and host-scoped |
| Raw backend container port / direct backend listener | forbidden-for-now | too low-level and bypasses the intended reviewed access posture | only reconsider behind a deliberate proxy boundary after real-testnet proof |
| Worker process / worker internals | local-only | execution internals, not user-facing and not review ingress | remain internal-only |
| Runtime env inspection (`TESTNET_EXCHANGE_*`, executor mode toggles) | operator-only | needed for guarded enablement and diagnosis, but too sensitive for broad exposure | preserve operator-only handling and no secret disclosure |
| `TESTNET_EXECUTOR_MODE=mock/real` and `TESTNET_EXECUTOR_REAL_ENABLE` usage | operator-only | these are guarded runtime switches, not user controls | require explicit operator review and signoff before `real` use |
| Preflight-only command execution path | operator-only | useful for bounded verification but still part of guarded engineering/testnet preparation | keep tied to review evidence and retreat posture |
| First bounded real testnet request execution | operator-only | highest-risk currently intended action; must stay tightly supervised | only after enablement checklist and signoff are complete |
| Review artifact creation for first real request | operator-only | review evidence is an operational control surface, not a public product surface | keep attached to named reviewer / operator process |
| `/commands` list view through controlled console path | future-public | this is a strong candidate for eventual stable operator-facing review UI, but current host posture is still engineering-heavy | requires durable ingress, access control, and stable real-testnet review semantics |
| `/commands/[id]` detail review page | future-public | central review endpoint, but not yet ready as a broad public entry | requires stable auth/access boundary and operator-grade evidence posture |
| `/ops` / kill switch surface | operator-only | safety-critical control plane; should never be casual public ingress | keep restricted to trusted operators with explicit runbook steps |
| Trade Gate UI for bounded internal use | future-public | plausible future operator/customer entry, but current stage still depends on controlled engineering access patterns | requires stable proxy/auth posture and post-first-real-request proof |
| Tunnel-based access path | operator-only | acceptable as a temporary controlled bridge while ingress stays intentionally narrow | phase down only after durable ingress is proven |
| Reverse proxy / durable web ingress | future-public | likely eventual shape for stable access, but not yet earned | requires proven real-testnet path, access control, and retreat confidence |
| Public domain / customer-visible hostname | future-public | useful only once the host should become a stable durable entrypoint | wait until first real request, review evidence, and ingress posture are stable |
| Direct real transport helper invocation outside canonical command path | forbidden-for-now | would bypass review/evidence semantics and weaken guardrails | never allow outside canonical `ORDER + execution_mode=testnet` path |
| Live trading executor path | forbidden-for-now | explicitly out of bounds; live remains NO-GO | only reconsider after separate live readiness, not as part of current testnet work |

## 3. Immediate interpretation

The matrix implies the current host should be treated as:

```text
engineering-controlled
operator-mediated
not broadly exposed
not customer-direct
```

This matches the current project stage.
It also explains why a domain is not yet the next meaningful step.

## 4. What may evolve next

The most likely near-term reclassification path is:

- `Trade Gate UI`: `future-public` remains unchanged until the first guarded real testnet request is proven
- `/commands` and `/commands/[id]`: may become more stable operator-facing ingress first
- tunnel-based access: should eventually shrink in importance once a durable operator ingress exists
- reverse proxy / domain: should remain deferred until the current guarded first-real-request milestone is complete

## 5. What should not move early

The following reclassification moves should not happen early:

- `raw backend container port` -> anything public
- `runtime toggles` -> anything customer-facing
- `real transport helper` -> direct callable surface
- `live trading executor` -> anything except forbidden-for-now

Those moves would widen exposure faster than the evidence and rollback posture currently justify.

## 6. Stable status statement

At this point the correct host access summary is:

```text
local runtime internals: local-only
guarded engineering/testnet actions: operator-only
review-facing console paths: future-public
raw backend and live execution surfaces: forbidden-for-now or not yet public
domain: still not required
live trading: NO-GO
```

## 7. Minimal next bounded round

After this matrix, the next natural host-related bounded round is:

```text
Cloud Host Access Enforcement Gap Review V1
```

Scope:

```text
docs-only
compare current matrix classes against actual known host/runtime access behavior
and record what is still policy-only versus what is already enforced in code/runtime
```

# Operator Domain Ingress Implementation Packet V1

**Status:** implementation-packet only. No DNS change, no ingress change, no auth deployment, no runtime mutation, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-06-08**

## 1. Purpose

This packet defines the narrow next infrastructure task that may be opened for operator-domain access.

It exists to answer:

```text
if the project chooses to move from SSH-tunnel-only review access
to a bounded domain-backed operator/reviewer entry,
what exactly should that implementation task contain?
```

This packet still does **not** implement DNS, ingress, or auth.
It only fixes the implementation shape so the later task stays narrow.

## 2. Current Posture

At the time of this packet:

- first bounded controlled real testnet send: **successful**
- successful execution closeout: present
- final reviewed PASS closeout: present
- real review artifact: present
- cloud host final alignment closeout: present
- current `main`: aligned with cloud host
- canonical `TESTNET_*` runtime contract: aligned
- cloud-host runtime alignment check: `PASS`
- live trading: `NO-GO`

That means the project is now strong enough to define a bounded ingress implementation packet.
It is still **not** strong enough to imply public product release or live trading.

## 3. First-Phase Goal

The first-phase operator-domain goal is:

```text
provide a bounded operator/reviewer web entry for review-first surfaces,
without exposing raw backend services and without implying product launch
```

The first phase is therefore:

- operator/reviewer only
- review-first
- evidence-first
- narrow in scope

The first phase is **not**:

- a public homepage
- a customer portal
- a raw API hostname
- a trading launch

## 4. Recommended First Hostname

Preferred first hostname class:

- `ops.<domain>`

Acceptable fallback:

- `review.<domain>`
- `console-review.<domain>`

Still not acceptable as the first hostname:

- `api.<domain>`
- `app.<domain>`
- `trade.<domain>`
- `live.<domain>`

The apex / bare domain remains deferred.

## 5. First-Phase Landing Surface

The first domain-backed landing surface should remain a narrow operator/reviewer entry.

Recommended visible web routes:

- `/`
- `/ops`
- `/commands`
- `/commands/[id]`

The landing page should:

1. state the current posture clearly
   - review-first
   - bounded operator/reviewer use
   - `go-live: NO-GO`
   - `live trading: NO-GO`
2. explain where to look first
   - `/ops`
   - `/commands`
   - `/commands/[id]`
3. avoid any customer or launch language

## 6. Public-Surface Boundary

The future ingress task must preserve all of the following:

- raw backend port `8000` remains non-public
- backend health/ops JSON must not be anonymously exposed on the public internet
- worker/runtime toggle surfaces remain unavailable
- secrets and env material remain unavailable
- exchange-executor helper paths remain unavailable

In short:

```text
the domain may front the operator/reviewer web surface,
but it must not front raw backend internals
```

## 7. Recommended First-Phase Architecture

The first-phase implementation should use this separation:

1. **Domain / DNS layer**
   - point a narrow hostname such as `ops.<domain>` at the stage ingress host

2. **TLS / reverse proxy layer**
   - terminate HTTPS at a bounded ingress tier
   - recommended classes:
     - Nginx
     - Caddy
     - equivalent reverse proxy with explicit route allowlist

3. **Access-boundary layer**
   - require explicit operator/reviewer access before page entry
   - acceptable first-phase classes:
     - Cloudflare Access / equivalent zero-trust gate
     - tightly scoped allowlist + auth gate
     - team-only bounded access layer

4. **Application layer**
   - expose only the operator/reviewer web surface
   - allow the web surface to use its existing proxy/read model
   - keep backend runtime private to the host/network

## 8. Route Policy For The Future Task

The later implementation task should define an explicit route policy like this:

### Allowed domain-backed web routes

- `/`
- `/ops`
- `/commands`
- `/commands/[id]`
- static assets required by the operator/reviewer web entry

### Forbidden domain-backed routes

- direct raw backend `:8000` exposure
- anonymous `/health` / `/ops/state` / `/ops/worker`
- mutation-heavy admin/debug endpoints
- worker/runtime control endpoints
- secret-bearing routes
- any path implying customer execution authority

If a future route cannot be justified as operator/reviewer review-first, it should stay out.

## 9. Allowed Work In The Future Implementation Task

The later infrastructure task may include:

- DNS record creation / update for the chosen narrow hostname
- HTTPS reverse-proxy configuration
- explicit access-boundary implementation
- firewall changes only as needed for the bounded ingress tier
- operator/reviewer landing-surface wiring
- rollback / retreat scripting and verification

## 10. Forbidden Work In The Future Implementation Task

Even that later task must still not include:

- live trading rollout
- production execution approval
- public anonymous review access
- direct raw backend publication
- worker/runtime toggle publication
- secret distribution changes unrelated to ingress
- mixing ingress rollout with unrelated executor/runtime refactors

## 11. Pre-Implementation Gate For Opening The Future Task

Before the future ingress implementation task begins, all of the following should still be true:

1. first-controlled-send actual artifact remains present
2. final reviewed PASS closeout remains present
3. cloud host final alignment closeout remains present
4. cloud-host runtime alignment remains `PASS`
5. hostname posture remains narrow
6. landing surface remains review-first
7. auth boundary remains non-public by default
8. raw backend exposure remains forbidden
9. `go-live` remains `NO-GO`
10. `live trading` remains `NO-GO`

If any one of these falls out of alignment, the future task should pause.

## 12. Implementation Checklist For The Later Task

The later task should explicitly answer all of these:

- chosen hostname:
  - `ops.<domain>` / `review.<domain>` / other narrow label
- DNS target:
  - host / record type / TTL
- TLS termination point:
  - Nginx / Caddy / equivalent
- access boundary:
  - exact first-phase auth class
- allowed routes:
  - exact allowlist
- blocked routes:
  - exact deny list
- rollback:
  - DNS rollback
  - proxy rollback
  - boundary rollback
- smoke checks:
  - domain-backed landing page reachable
  - `/ops`
  - `/commands`
  - `/commands/[id]`
  - raw backend still not publicly reachable

## 13. STOP Conditions

Stop the future task immediately if:

- the hostname starts implying public product launch
- the landing surface becomes broader than operator/reviewer review
- raw backend publication becomes coupled to the same rollout
- access boundary becomes optional or ambiguous
- `go-live` / `live trading` language starts leaking into ingress rollout
- rollback steps cannot be written cleanly

## 14. Rollback / Retreat

If this implementation packet starts being treated as public-ingress approval:

1. stop
2. retreat to the auth-boundary, landing-surface, and DNS-deferral decisions
3. keep DNS untouched
4. keep ingress untouched
5. reopen only with the bounded operator/reviewer posture restored

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 15. One-Line Rule

```text
The next operator-domain task, if opened, should implement a narrow operator/reviewer HTTPS entry such as ops.<domain> behind an explicit access boundary, while keeping raw backend services non-public and preserving go-live/live-trading NO-GO status.
```

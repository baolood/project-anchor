# Cloud host access enforcement gap review V1

**Status:** enforcement review only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** compare the current cloud-host access class matrix against what is already enforced in code/runtime today, versus what is still only a policy expectation or operator discipline rule.

This review does not change ingress, deploy shape, domain posture, or live-trading scope.

## 1. Decision

The current cloud-host access posture is:

```text
partially enforced in code/runtime
partially enforced only by operator discipline
not yet ready for broad public ingress
```

Meaning:

- several important testnet boundaries are already real guardrails in backend code
- several host-access boundaries still rely on deployment shape, operator restraint, or review process
- the main next host question is no longer classification
- the main next host question is which high-value boundaries should move from policy-only into stronger runtime or ingress enforcement

## 2. What is already enforced in code/runtime

The following boundaries are no longer just written policy.
They are already concretely enforced in backend/runtime behavior.

### A. Canonical testnet command path is enforced

Current real/mock testnet execution work is constrained to:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This means the project is not leaving testnet execution semantics open-ended at runtime.

### B. Kill switch is enforced before external request

`anchor-backend/app/actions/runner.py` already calls merged kill-switch state before the testnet external boundary.

Effect:

- `KILL_SWITCH_ON` is a real runtime stop, not just a runbook suggestion
- it blocks before external request evidence is allowed to appear

### C. Host-safety allowlist is enforced

`runner.py` already validates `TESTNET_EXCHANGE_BASE_URL` through normalized origin rules and venue profile allowlists.

Effect:

- localhost-style or malformed origins are rejected
- origin drift does not silently become a real external request
- “use the right host” is partially runtime-enforced, not just documented

### D. Credential presence is enforced

The testnet preflight currently rejects missing canonical credentials.

Effect:

- `TESTNET_CREDENTIALS_MISSING` is a real preflight family
- the system does not proceed toward real request mode without the canonical environment variables

### E. Real mode is explicitly gated

`anchor-backend/app/executors/testnet_order_executor.py` already requires:

```text
TESTNET_EXECUTOR_MODE=real
TESTNET_EXECUTOR_REAL_ENABLE=1
```

before the real helper is allowed to leave fail-closed posture.

Effect:

- accidental drift from mock to real is materially harder
- “real request” is currently an explicit operator enablement act

### F. Transport input is validated before signed HTTP

The real helper already rejects unsupported market/order type or invalid size assumptions with:

- `TESTNET_REAL_TRANSPORT_INPUT_INVALID`
- `TESTNET_CREDENTIALS_MISSING`
- `TESTNET_REAL_WIRE_DISABLED`

Effect:

- the helper does not blindly attempt signed HTTP
- boundary mistakes can still fail locally with normalized evidence

## 3. What is enforced mostly by deployment/runtime shape

The following boundaries are not primarily enforced by application code alone, but are still materially constrained by current host posture.

### A. Raw backend port non-publicity

The project’s current safety posture depends partly on how the host is run and exposed.

Effect today:

- this boundary may be effectively narrow in practice
- but that narrowness is still a host/deploy property, not a strong app-level public-ingress policy engine

### B. Tunnel-style access staying operator-only

This is currently enforced more by who has SSH/operator access than by product-layer access control.

Effect today:

- acceptable for current engineering stage
- not equivalent to a durable access-control system

### C. `/ops`, `/commands`, `/commands/[id]`, and Trade Gate exposure level

These surfaces are partly shaped by current environment and usage pattern, not yet by a finished durable access boundary.

Effect today:

- they can be used in controlled flows
- they are not yet proven as stable public or customer-facing ingress

## 4. What is still mostly policy-only

The following boundaries are still mostly written down, reviewed, and expected operationally, but not yet strongly enforced in code/runtime.

### A. “Operator-only” as a first-class access concept

Today, “operator-only” is more of a process rule than a full technical access-control layer.

There is not yet a demonstrated product boundary that says:

```text
this surface is technically available only to authenticated operator roles
```

### B. “Future-public” versus “not yet public”

The matrix now classifies these cleanly, but the project still lacks a finalized ingress mechanism that technically enforces the distinction.

### C. Public domain deferral

Today this is a correct decision, but it is still a strategic posture rather than a runtime-enforced invariant.

### D. Review artifact handling discipline

The review mini-bundle is mature, but the rules about where real artifacts live, who fills them, and how they are approved remain process-heavy rather than system-enforced.

## 5. Highest-value enforcement gaps

The most important remaining enforcement gaps are:

1. durable ingress/access control for review-facing UI surfaces
2. stronger technical separation between operator-only and future-public surfaces
3. explicit host-level confirmation that raw backend ingress is not accidentally widening
4. tighter runtime proof that real-mode enablement and retreat posture are observable and reversible during first real request work

These matter more right now than domain or presentation polish.

## 6. What does not need urgent enforcement yet

The following do not need to become stronger immediately:

- public domain routing
- customer-facing self-service ingress
- broader productized public access

Those would be premature before the first bounded real testnet request is fully proven and reviewed.

## 7. Recommended next host-related step

The most useful next host-related bounded round is:

```text
Cloud Host Access Minimal Ops Baseline V1
```

Scope:

```text
docs-only
record the minimum operator checks for host state, logs, process/container posture,
and retreat actions that should accompany the first guarded real testnet request
```

This would help convert some of the current policy-only boundary into repeatable operational enforcement.

## 8. Stable status statement

At this point the correct enforcement summary is:

```text
kill switch / host safety / credential presence / real-mode gate: enforced
raw ingress narrowness / tunnel discipline / operator-only posture: partly environmental or procedural
future-public versus public-ready: classified, not yet fully enforced
domain: still not required
live trading: NO-GO
```

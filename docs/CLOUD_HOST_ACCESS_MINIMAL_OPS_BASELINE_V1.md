# Cloud host access minimal ops baseline V1

**Status:** operator baseline only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the minimum operator checks for cloud-host state, process posture, logs, runtime mode, and immediate retreat actions that should be completed before or during the first guarded real testnet request window.

This baseline does not approve public ingress, domains, or live trading.
It standardizes the smallest acceptable operator posture around the current guarded cloud-host workflow.

## 1. Decision

Before the first guarded real testnet request, the cloud host should not be treated as “ready” unless the operator can complete a minimum host-side baseline in one pass.

If the operator cannot answer these checks quickly and clearly, result is:

```text
BLOCKED - do not proceed beyond mock or fail-closed posture
```

## 2. What this baseline is for

This baseline exists to cover the host/runtime gaps that are not yet fully enforced by code alone.

It is specifically meant to reduce ambiguity around:

- host access state
- container/process posture
- runtime mode drift
- log visibility
- retreat actions if the first real request behaves unexpectedly

It is not a general operations handbook.
It is a minimum first-real-request host checklist.

## 3. Minimum host-state checks

Before the request window, the operator should confirm all of these:

1. The intended cloud host is the correct one for this bounded request.
2. Shell access is limited to the responsible operator(s) for this window.
3. The working tree or deployed revision being inspected is the intended revision for the bounded request.
4. No unrelated ad hoc changes are being relied on.
5. The host is still being treated as an engineering-controlled node, not a public customer ingress.

If any of these are uncertain, stop before runtime enablement.

## 4. Minimum process/container posture checks

The operator should be able to identify, at minimum:

- backend process/container is up
- worker process/container is up
- no obviously stale crashed process is being mistaken for a healthy one
- the expected review surfaces are reachable through the current controlled access path

This does not require a full observability stack.
It does require enough clarity to avoid “we thought the right service was running.”

## 5. Minimum runtime posture checks

Before the real request window, the operator should explicitly confirm:

- canonical path remains `ORDER + execution_mode=testnet`
- `TESTNET_EXECUTOR_MODE` value is intentional
- `TESTNET_EXECUTOR_REAL_ENABLE` value is intentional
- canonical `TESTNET_EXCHANGE_*` naming is the only source being relied on
- kill switch merged state can be checked
- host safety origin is the expected one
- retreat to `mock` or fail-closed posture remains immediately possible

If any runtime value appears inherited, stale, or ambiguous, result is `BLOCKED`.

## 6. Minimum log visibility checks

The operator should confirm they can quickly inspect enough logs or output to answer:

- did the command stay in preflight refusal?
- did it cross into `TESTNET_EXECUTOR_REQUESTED`?
- did it reach `TESTNET_EXECUTOR_ACCEPTED` or `TESTNET_EXECUTOR_REJECTED`?
- did the final state become `DONE` or `FAILED`?
- is there any sign of contradictory evidence?

If the operator cannot answer those questions within the current controlled access flow, the host posture is not ready for the bounded request.

## 7. Minimum review-surface checks

The operator must still be able to follow the fixed review path:

```text
/ops
-> /commands
-> /commands/[id]
```

At minimum, they should be able to verify:

- whether the system was in mock or real mode
- whether external request evidence exists
- whether the normalized result family is understandable
- whether retreat is required before any second attempt

Terminal output alone is not sufficient.

## 8. Minimum retreat actions

Before the first guarded real request, the operator should already know the immediate retreat moves:

1. stop further real attempts
2. return to `mock` or fail-closed posture
3. preserve evidence for `/commands/[id]` and review artifact creation
4. do not perform a “quick second try”
5. route the result into the signed review path before any follow-up action

If retreat depends on improvisation, the baseline is incomplete.

## 9. Minimum red flags that cause BLOCKED

Treat the host as `BLOCKED` for real-request work if any of these are true:

- wrong host or uncertain host identity
- backend/worker posture is unclear
- runtime mode is inherited or ambiguous
- canonical env source is not clear
- kill switch state is unavailable or unclear
- host-safety origin is not plainly confirmable
- log visibility is too weak to distinguish preflight vs external attempt
- `/commands/[id]` review path is unavailable
- retreat path is not immediate

These are operator baseline failures, not “maybe fine” warnings.

## 10. What this baseline does not require yet

This baseline does not require:

- public domain
- customer-facing ingress
- broad public access control rollout
- live-trading readiness
- full observability platform

Those are later-stage concerns.
The current goal is simply to make the first guarded real testnet window operationally legible.

## 11. Stable status statement

At this point the correct operator baseline summary is:

```text
code guardrails exist for preflight and real-mode gating
host/operator posture still needs an explicit minimum operational checklist
first guarded real testnet request should remain BLOCKED without this baseline
domain: still not required
live trading: NO-GO
```

## 12. Minimal next bounded round

After this baseline, the next natural host-related bounded round is:

```text
Cloud Host Access Retreat Drill Spec V1
```

Scope:

```text
docs-only
define the smallest retreat drill for switching from real-attempt posture
back to mock or fail-closed posture after a bounded anomaly
```

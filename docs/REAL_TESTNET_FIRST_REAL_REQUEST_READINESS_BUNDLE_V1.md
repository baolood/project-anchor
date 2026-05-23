# Real Testnet first real request readiness bundle V1

**Status:** readiness bundle only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-23

**Scope:** provide one bounded entrypoint for the exact materials required before Project Anchor is allowed to attempt the first real external testnet request on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This bundle does not authorize the request. It only compresses the required decision, contract, review, and retreat materials into one review order.

## 1. Decision

This bundle is authoritative only for:

```text
ORDER + execution_mode=testnet
```

It must not be used to justify:

```text
legacy QUOTE + BINANCE_TESTNET
TESTNET_EXECUTOR_STUB
live trading
```

## 2. Bundle objective

The goal is narrow:

```text
before the first real request,
everyone should know exactly what to read,
what must already be true,
what evidence must remain absent,
and how to retreat immediately if the request looks wrong
```

This bundle exists because the full real-testnet document stack is now broad enough that “read everything” is no longer a practical preflight.

## 3. Required reading order

Read this bundle in sequence.

### A. Path identity and legacy exclusion

1. [docs/TESTNET_COMMAND_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_COMMAND_CONTRACT_V1.md)
2. [docs/LEGACY_TESTNET_PATH_DECISION_V1.md](/Users/baolood/Projects/project-anchor/docs/LEGACY_TESTNET_PATH_DECISION_V1.md)
3. [docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md](/Users/baolood/Projects/project-anchor/docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md)

Purpose:

```text
confirm the first real request belongs only to the canonical ORDER testnet path
and that legacy QUOTE behavior is not being mistaken for readiness
```

### B. Runtime safety prerequisites

4. [docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md)
5. [docs/TESTNET_SECRETS_CUSTODY_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_SECRETS_CUSTODY_V1.md)
6. [docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md)
7. [docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_KILL_SWITCH_SOURCE_RULE_V1.md)

Purpose:

```text
confirm canonical env names,
credential custody posture,
exact host allowlist,
and authoritative kill-switch source
```

### C. Boundary behavior that must stay true before real wire

8. [docs/REAL_TESTNET_BOUNDARY_PREFLIGHT_ACCEPTANCE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_BOUNDARY_PREFLIGHT_ACCEPTANCE_V1.md)
9. [docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md](/Users/baolood/Projects/project-anchor/docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md)
10. [docs/REAL_TESTNET_REAL_TRANSPORT_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_REAL_TRANSPORT_CONTRACT_V1.md)
11. [docs/REAL_TESTNET_EXTERNAL_EXECUTOR_REAL_WIRE_PLAN_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EXTERNAL_EXECUTOR_REAL_WIRE_PLAN_V1.md)

Purpose:

```text
confirm preflight refusal still works,
kill switch still stops before signed HTTP,
transport input/output is normalized,
and the real-wire plan is still deliberately narrow
```

### D. Reviewer interpretation and evidence

12. [docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md)
13. [docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVENT_PAYLOAD_SCHEMA_V1.md)
14. [docs/REAL_TESTNET_SUCCESS_SHAPE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_SUCCESS_SHAPE_RULE_V1.md)
15. [docs/REAL_TESTNET_FAILURE_SHAPE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_SHAPE_RULE_V1.md)
16. [docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md)
17. [docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md)

Purpose:

```text
give reviewers one shared way to interpret requested/accepted/rejected evidence,
final success/failure shape,
and negative evidence requirements
```

### E. Final first-request gate

18. [docs/REAL_TESTNET_FIRST_REAL_REQUEST_GUARDRAIL_REVIEW_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_GUARDRAIL_REVIEW_V1.md)

Purpose:

```text
compress the final go/no-go questions,
required positive evidence,
required negative evidence,
and immediate retreat posture
```

## 4. Minimal review outputs this bundle must enable

After reading this bundle, the reviewer must be able to answer all of these without guesswork:

1. Is the path definitely canonical `ORDER + execution_mode=testnet`?
2. Are canonical `TESTNET_EXCHANGE_*` runtime prerequisites understood?
3. Can host safety and kill switch proof be explained before signed HTTP?
4. Can mocked evidence and real evidence be distinguished cleanly?
5. What exact event chain would count as:
   - preflight refusal
   - external-attempt failure
   - canonical real success
6. What exact anomaly should trigger immediate retreat to mock-only or fail-closed posture?

If the bundle cannot answer those questions, it is incomplete.

## 5. Hard blockers that remain

This bundle does not remove any blocker by itself. The first real request remains blocked if any of these are still unresolved:

- `TESTNET_EXECUTOR_MODE` can drift into real unintentionally
- host/origin evidence is ambiguous
- credential presence cannot be proven safely
- `/commands/[id]` cannot explain real-attempt evidence clearly
- kill switch proof at the real boundary is still ambiguous
- rollback to `mock` or fail-closed posture is not immediate
- live trading posture is anything other than `NO-GO`

## 6. Recommended reviewer sequence by role

### Engineering / release lead

Read sections A -> E in order.

### Operator

Start with:

- [docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md)
- [docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md)
- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_GUARDRAIL_REVIEW_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_GUARDRAIL_REVIEW_V1.md)

Then return to sections B and C if any safety answer is unclear.

### Security / custody reviewer

Start with:

- [docs/TESTNET_SECRETS_CUSTODY_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_SECRETS_CUSTODY_V1.md)
- [docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md)
- [docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_HOST_SAFETY_RULE_V1.md)

## 7. What this bundle does not mean

This bundle does **not** mean:

- real testnet is approved
- real credentials are loaded
- one real request is automatically safe
- deploy/runtime drift is solved
- live trading is approved

It only means the first-real-request review stack is now organized enough to be run deliberately.

## 8. Minimal next bounded round

After this bundle, the most natural next bounded round is:

```text
Real Testnet First Real Request Enablement Checklist V1
```

Scope:

```text
docs-only
compress the exact runtime toggles and reviewer signoff steps
required immediately before flipping from mock to real
```

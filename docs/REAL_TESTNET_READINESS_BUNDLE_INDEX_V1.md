# Real testnet readiness bundle index V1

**Status:** bundle index only - no real key, no external API call, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-22

**Scope:** provide a single entrypoint for the current real-testnet readiness document stack under the canonical future path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This index does not enable real testnet or live trading. It only organizes the current decision, review, and operator docs into one sequence.

## 1. Decision

This readiness bundle is authoritative only for:

```text
ORDER + execution_mode=testnet
```

It is not an entrypoint for:

```text
QUOTE + EXECUTION_MODE=BINANCE_TESTNET
TESTNET_EXECUTOR_STUB
live trading
```

## 2. What this bundle is for

The goal is simple:

```text
one place to start,
one order to read,
one shared vocabulary for review
```

Without an index, the stack is already large enough that operators can miss a required doc or read them in the wrong order.

## 3. Recommended reading order

Read the bundle in this sequence.

### A. High-level posture and gaps

1. [docs/TESTNET_READINESS_GAP_REVIEW_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_READINESS_GAP_REVIEW_V1.md)
2. [docs/REAL_TESTNET_GAP_REVIEW_V2.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_GAP_REVIEW_V2.md)

Purpose:

```text
understand what the repo can do now,
what remains blocked,
and why real testnet is still NO-GO
```

### B. Canonical path decisions

3. [docs/TESTNET_COMMAND_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_COMMAND_CONTRACT_V1.md)
4. [docs/LEGACY_TESTNET_PATH_DECISION_V1.md](/Users/baolood/Projects/project-anchor/docs/LEGACY_TESTNET_PATH_DECISION_V1.md)
5. [docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md)

Purpose:

```text
fix the canonical ORDER contract,
exclude legacy QUOTE as the future path,
and fix env naming before implementation
```

### C. Security and custody preconditions

6. [docs/TESTNET_SECRETS_CUSTODY_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_SECRETS_CUSTODY_V1.md)

Purpose:

```text
define how future testnet credentials are handled
without putting any secret into git
```

### D. Stub and pre-real groundwork

7. [docs/TESTNET_STUB_RUNBOOK_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_STUB_RUNBOOK_V1.md)
8. [docs/TESTNET_STUB_REVIEW_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_STUB_REVIEW_CHECKLIST_V1.md)

Purpose:

```text
preserve the boundary between local stub evidence
and future real external evidence
```

### E. Real executor boundary and smoke design

9. [docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md](/Users/baolood/Projects/project-anchor/docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md)
10. [docs/REAL_TESTNET_SMOKE_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_SMOKE_SPEC_V1.md)
11. [docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md](/Users/baolood/Projects/project-anchor/docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md)

Purpose:

```text
define where the real executor boundary belongs,
what the first real smoke must prove,
and how kill switch proof must work before signed HTTP
```

### F. Review vocabulary and evidence compression

12. [docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md)
13. [docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md)
14. [docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md)
15. [docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md)

Purpose:

```text
fix failure families,
compress expected evidence,
and standardize manual operator review
```

## 4. Minimum bundle subsets by task

Use these smaller subsets depending on the question.

### “Are we ready for real testnet?”

Read:

- [docs/REAL_TESTNET_GAP_REVIEW_V2.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_GAP_REVIEW_V2.md)
- [docs/LEGACY_TESTNET_PATH_DECISION_V1.md](/Users/baolood/Projects/project-anchor/docs/LEGACY_TESTNET_PATH_DECISION_V1.md)
- [docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md)

### “What is the canonical future path?”

Read:

- [docs/TESTNET_COMMAND_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_COMMAND_CONTRACT_V1.md)
- [docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md](/Users/baolood/Projects/project-anchor/docs/ORDER_TESTNET_EXECUTOR_BOUNDARY_V1.md)

### “What should the first real smoke prove?”

Read:

- [docs/REAL_TESTNET_SMOKE_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_SMOKE_SPEC_V1.md)
- [docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md](/Users/baolood/Projects/project-anchor/docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md)

### “How do I review a command result?”

Read:

- [docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FAILURE_TAXONOMY_V1.md)
- [docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md)
- [docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md)
- [docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md)

## 5. Bundle guardrails

This bundle must always preserve these guardrails:

- canonical path is `ORDER + execution_mode=testnet`
- legacy `QUOTE` path is not treated as future proof
- stub evidence is not treated as real-executor proof
- credentials stay outside git
- kill switch proof is mandatory before signed HTTP
- live trading remains `NO-GO`

## 6. What this bundle does not mean

This index does **not** mean:

- real testnet is enabled
- testnet keys are present
- external API calls are approved
- deploy work is approved
- live trading is approved

It only means the document stack is now organized enough to follow consistently.

## 7. Suggested usage order by role

### Engineering lead

Read sections A -> F in order.

### Operator / reviewer

Start with:

- [docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_OPERATOR_RUNBOOK_V1.md)
- [docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_REVIEW_CHECKLIST_V1.md)
- [docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_EVIDENCE_MATRIX_V1.md)

### Security / custody reviewer

Start with:

- [docs/TESTNET_SECRETS_CUSTODY_V1.md](/Users/baolood/Projects/project-anchor/docs/TESTNET_SECRETS_CUSTODY_V1.md)
- [docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md](/Users/baolood/Projects/project-anchor/docs/CANONICAL_TESTNET_ENV_CONTRACT_V1.md)

## 8. Recommended next bounded round

After this index, the natural next round is:

```text
Real Testnet Open Questions Register V1
```

Scope:

```text
docs-only
collect the remaining unanswered questions that still block real testnet implementation
no real key
no live trading
```

## 9. Acceptance for this index

```text
single readiness entrypoint created: PASS
canonical reading order fixed: PASS
task-based doc subsets stated: PASS
bundle guardrails stated: PASS
stub and legacy path excluded as canonical proof: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

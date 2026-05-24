# Real testnet review artifact reviewer notes rubric V1

**Status:** rubric only - no real key, no external API call, no live trading approval.

**Purpose:** define what good `notes` content should look like inside a first-real-request review artifact, so different reviewers produce comparable explanations across `BLOCKED`, `PASS`, and `FAIL`.

Canonical path only:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This rubric evaluates the `notes` section of the artifact, not the whole real-testnet readiness stack.

## 1. What good notes should answer

Good notes should answer these five questions in plain language:

1. Why was this request allowed to proceed, blocked, or failed?
2. What exact runtime posture and host/origin identity were in effect?
3. What happened at the evidence level: blocked before external attempt, accepted cleanly, or attempted but contradictory?
4. Was retreat required before any second attempt?
5. What is the next safe action?

If the notes do not answer these questions, they are incomplete.

## 2. Minimum content expectations

A good notes section should mention:

- the result label meaning in this specific case
- whether external attempt happened
- whether the evidence was internally consistent
- whether retreat is required
- whether a second request is allowed, blocked, or pending further review

It should avoid vague phrases like:

- "looks okay"
- "probably fine"
- "something failed"
- "needs checking"

without explaining what exactly happened.

## 3. Result-specific notes guidance

### `BLOCKED`

Good notes should make clear:

- what prerequisite was missing or ambiguous
- that the request did not cross into external attempt
- why stopping was the correct action
- what must be fixed before a future attempt

### `PASS`

Good notes should make clear:

- why the result is considered internally consistent
- that the expected evidence chain would be reviewable
- that no contradiction was observed
- whether the result implies anything about a second request

### `FAIL`

Good notes should make clear:

- that the request crossed the boundary far enough to become unsafe or contradictory
- what evidence or behavior made it fail-worthy
- why retreat is mandatory
- why the result is not merely `BLOCKED`

## 4. Strong vs weak notes

### Strong notes

Strong notes are:

- specific
- non-secret
- tied to the result label
- clear about next action

### Weak notes

Weak notes are:

- generic
- emotionally phrased instead of evidence-based
- missing the distinction between `BLOCKED`, `PASS`, and `FAIL`
- silent about retreat or next action

## 5. Quick self-check for reviewers

Before finalizing notes, ask:

- could another reviewer understand the result without reading my terminal?
- did I state whether external attempt happened?
- did I state whether retreat is required?
- did I explain why this is this label and not one of the other two?
- did I avoid secrets?

If any answer is `no`, improve the notes before finalizing.

## 6. Example alignment

Compare your notes style against:

- [BLOCKED example](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-23_order-example-blocked.md)
- [PASS example](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-23_order-example-pass.md)
- [FAIL example](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-24_order-example-fail.md)

These are synthetic, but they show the intended level of explicitness.

## 7. Minimal next bounded round

After this rubric, the next natural bounded round is:

```text
Real Testnet Review Artifact Bundle Index V1
```

Scope:

```text
docs-only
compress README, INDEX, checklist, notes rubric,
and three examples into one final mini-bundle entrypoint
```

# Real testnet review artifact checklist V1

**Status:** checklist only - no real key, no external API call, no live trading approval.

**Purpose:** give reviewers one very short checklist for validating the review artifact itself inside `docs/reviews/real_testnet/`, without reopening the full first-real-request document stack.

Canonical path only:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This checklist does not approve a real request by itself. It only checks whether the artifact record is complete, reviewable, and non-secret.

## 1. Use this checklist for one question only

Ask:

```text
is this review artifact itself acceptable as a record?
```

Do not use this checklist as a substitute for:

- readiness review
- enablement checklist
- kill-switch boundary review
- real request authorization

## 2. Artifact identity

Confirm all of these:

- filename matches `FIRST_REAL_REQUEST_<date>_<command_id-or-example>.md`
- file clearly states whether it is synthetic or real
- file clearly states canonical path `ORDER + execution_mode=testnet`
- file is stored under `docs/reviews/real_testnet/`

If any of these fail, mark artifact review `FAIL`.

## 3. Required fields present

Confirm the artifact includes:

- reviewer
- operator
- executor mode
- host label
- configured origin
- command shape
- result label
- final command state
- normalized family
- external request status
- notes

If one of these is missing, mark artifact review `FAIL`.

## 4. Result label coherence

Check that the label matches the story in the notes.

### `BLOCKED`

Should mean:

- request did not proceed into external attempt
- artifact explains why

### `PASS`

Should mean:

- request is presented as internally consistent
- artifact explains why it is reviewable

### `FAIL`

Should mean:

- request crossed the boundary or behaved unsafely enough that retreat is required
- artifact explains the contradiction or unsafe condition

If the label and explanation disagree, mark artifact review `FAIL`.

## 5. Secret check

Confirm the artifact does **not** contain:

- API key
- API secret
- raw auth header
- signature
- plaintext credential dump

If any secret appears, mark artifact review `FAIL`.

## 6. Correlation check

Confirm the artifact gives enough information to correlate with review evidence:

- `command_id` or explicit `not-sent`
- `idempotency_key`
- `host_label`
- `configured_origin`
- final result label

If correlation would require guessing, mark artifact review `FAIL`.

## 7. Minimal result

Use one of:

- `PASS` = artifact is complete, coherent, and non-secret
- `FAIL` = artifact is incomplete, contradictory, or unsafe to use as review evidence

This checklist does not need a separate `BLOCKED` result because it is evaluating the artifact, not the request.

## 8. Fast entrypoints

For examples, compare against:

- [BLOCKED example](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-23_order-example-blocked.md)
- [PASS example](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-23_order-example-pass.md)
- [FAIL example](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-24_order-example-fail.md)

For directory rules, see:

- [README.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/README.md)
- [INDEX.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/INDEX.md)

## 9. Minimal next bounded round

After this checklist, the next natural bounded round is:

```text
Real Testnet Review Artifact Reviewer Notes Rubric V1
```

Scope:

```text
docs-only
define what good notes should look like inside the artifact,
so reviewers write comparable explanations across PASS/BLOCKED/FAIL
```

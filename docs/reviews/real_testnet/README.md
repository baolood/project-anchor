# Real testnet review artifacts

**Status:** directory readme only - no real key, no external API call, no live trading approval.

**Purpose:** explain what belongs in `docs/reviews/real_testnet/`, how files should be named, and how to choose between `BLOCKED`, `PASS`, and `FAIL` review artifacts for the first bounded real external testnet request on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This directory is not proof that a real external testnet request has already happened. It is the review-artifact home defined by:

- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_STORAGE_LOCATION_DECISION_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_STORAGE_LOCATION_DECISION_V1.md)

## 1. What belongs here

This directory should contain only:

- filled or synthetic first-request review artifacts
- one file per bounded review event
- non-secret review-safe material that correlates with `command_id` and `/commands/[id]`

This directory should not contain:

- runbooks
- reusable templates
- raw secrets
- terminal dumps presented without review context

## 2. Naming rule

Use filenames shaped like:

```text
FIRST_REAL_REQUEST_<date>_<command_id-or-example>.md
```

Examples:

- `FIRST_REAL_REQUEST_2026-05-23_order-example-blocked.md`
- `FIRST_REAL_REQUEST_2026-05-23_order-example-pass.md`
- future real record: `FIRST_REAL_REQUEST_2026-05-24_order-123abc.md`

Rules:

- include the review date
- include either the real `command_id` or an obvious synthetic suffix like `order-example-pass`
- never include secrets in the filename

## 3. Which result label to use

Choose exactly one result label per artifact.

### `BLOCKED`

Use when:

- the request was intentionally not sent
- prerequisites were incomplete
- runtime posture was ambiguous
- the team stopped before any external attempt

### `PASS`

Use when:

- the first bounded request was deliberately attempted
- the evidence chain was reviewable
- the final outcome was explainable and consistent
- no contradiction appeared between runtime posture and observed evidence

### `FAIL`

Use when:

- the request was sent under contradictory conditions
- the evidence chain became non-reviewable
- expected retreat posture failed
- the result cannot be explained safely

## 4. Current synthetic examples

This directory currently contains two synthetic examples:

- [FIRST_REAL_REQUEST_2026-05-23_order-example-blocked.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-23_order-example-blocked.md)
- [FIRST_REAL_REQUEST_2026-05-23_order-example-pass.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-23_order-example-pass.md)

They exist only to demonstrate format and result labeling.

## 5. Secret rule

Artifacts in this directory must remain non-secret.

Allowed:

- `command_id`
- `idempotency_key`
- `host_label`
- `configured_origin`
- normalized family
- result label

Not allowed:

- API key
- API secret
- raw auth header
- request signature
- plaintext credential dumps

## 6. Minimal next bounded round

After this readme, the next natural bounded round is:

```text
Real Testnet First Real Request FAIL Artifact Example V1
```

Scope:

```text
docs-only
add one synthetic FAIL artifact example so all three result labels
BLOCKED / PASS / FAIL are represented in this directory
```

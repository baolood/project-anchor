# First Controlled Send final review classification schema V1

**Status:** classification schema only - no baseline change, no runtime mutation, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-28**

**Scope:** define the minimum final-review classification schema that should decide how the first controlled real external testnet send is finally judged once the bounded review stack is assembled.

This document does not add a new operational layer.
It does not authorize a send, replace review artifacts, or change baseline behavior.
It only defines how the final reviewed conclusion should be classified.

## 1. Decision

The first controlled send needs one explicit final classification schema so the project can answer, in one bounded review step:

```text
was the first controlled send attempted,
what final outcome class applied,
did any external request actually start,
was any external order identity observed,
which evidence fields were mandatory,
and what final reviewer conclusion should be recorded
```

Without this schema, the project can accumulate many valid review artifacts but still fail to state one final reviewed conclusion consistently.

## 2. What this schema is for

This schema exists to normalize the final judgment surface for the first controlled send.

It should make these questions mechanically answerable:

1. `attempted` or `not_attempted`?
2. `blocked`, `failed`, or `succeeded`?
3. did an external request actually start: `true` or `false`?
4. was an external order id observed: `present` or `absent`?
5. was `command_id` required in this case?
6. was runtime-window proof required in this case?
7. what final reviewer verdict should be recorded?
8. where does the supporting evidence live?

It is not:

- a replacement for the final review closeout
- a new wrapper around existing records
- a send authorization surface
- a live trading exception

## 3. Classification axes

Every final reviewed classification must include all of these axes.

### A. Attempt status

Use exactly one:

- `ATTEMPTED`
- `NOT_ATTEMPTED`

### B. Final outcome class

Use exactly one:

- `BLOCKED`
- `FAILED`
- `SUCCEEDED`

### C. External request started

Use exactly one:

- `true`
- `false`

### D. External order id state

Use exactly one:

- `present`
- `absent`

### E. Final reviewer verdict

Use exactly one short normalized verdict label:

- `REVIEW_CONFIRMED_BLOCKED`
- `REVIEW_CONFIRMED_FAILED`
- `REVIEW_CONFIRMED_SUCCEEDED`
- `REVIEW_INCOMPLETE`
- `REVIEW_CONTRADICTED`

## 4. Required evidence pointer fields

Every final reviewed classification record should include these evidence-pointer fields.

### Mandatory in every case

- `classification_id`
- `review_date`
- `operator`
- `final_reviewer`
- `canonical_path`
- `execution_mode`
- `signoff_record_ref`
- `window_open_record_ref`
- `runtime_verification_record_ref`
- `attempt_record_ref`
- `final_review_closeout_ref`
- `review_artifact_ref`
- `notes`

### Mandatory when available from real runtime artifacts

- `command_id`
- `command_detail_ref`
- `external_order_id`

If a field in this section is absent, the classification must say why it is absent.

## 5. Field requirement rules

This schema must make field requirements explicit rather than implied.

### A. `command_id`

`command_id` is:

- **required** when `attempt_status = ATTEMPTED`
- **required** when `external_request_started = true`
- **required** when any real command-detail review was performed
- **optional** only when `attempt_status = NOT_ATTEMPTED` and the bounded stop occurred before a real command object existed

If `command_id` is missing when required, the final outcome class must not be `SUCCEEDED`.
It should generally land on `BLOCKED` or `FAILED` depending on whether the stop was bounded or contradictory.

### B. Runtime-window proof

`runtime_window_proof` is:

- **required** when `attempt_status = ATTEMPTED`
- **required** when any final outcome claims `SUCCEEDED`
- **required** when any final outcome claims `FAILED` after a real opened-window step
- **optional** only when `attempt_status = NOT_ATTEMPTED` and the stop occurred before a real opened window was claimed

Accepted runtime-window proof should point to concrete opened-window and runtime-verification evidence, not memory alone.

### C. `external_order_id`

`external_order_id` is:

- **present** only when real evidence supports that an external order identity existed
- **absent** when no such identity is shown in the review evidence

`external_order_id = absent` does not by itself imply `BLOCKED`.
It only means the review stack must not pretend that an external order identity was observed.

## 6. Allowed classification combinations

The final schema should permit only the following high-level combinations.

### A. `NOT_ATTEMPTED + BLOCKED`

Use when:

- the first controlled send correctly stopped before a real attempt
- `external_request_started = false`
- `external_order_id = absent`
- `command_id` may be optional if no real command object existed
- runtime-window proof may be optional if the stop occurred before a real opened window

Required verdict:

- `REVIEW_CONFIRMED_BLOCKED` or `REVIEW_INCOMPLETE`

### B. `ATTEMPTED + BLOCKED`

Use when:

- an attempt surface was entered and recorded
- but the reviewed conclusion is that the send remained bounded and did not become a completed successful send
- `command_id` is required
- runtime-window proof is required
- `external_request_started` may still be `false` if the attempt stopped before a real outbound request
- `external_order_id` may remain `absent`

Required verdict:

- `REVIEW_CONFIRMED_BLOCKED`

### C. `ATTEMPTED + FAILED`

Use when:

- the project crossed into a real attempted path
- real evidence shows the attempt did not succeed cleanly
- `command_id` is required
- runtime-window proof is required
- `external_request_started` may be `true` or `false`, but must be explicit
- `external_order_id` may be `present` or `absent`, but must be explicit

Required verdict:

- `REVIEW_CONFIRMED_FAILED` or `REVIEW_CONTRADICTED`

### D. `ATTEMPTED + SUCCEEDED`

Use only when:

- the bounded first controlled send was actually attempted
- the review stack is coherent
- `command_id` is required
- runtime-window proof is required
- `external_request_started = true`
- `external_order_id = present`
- the final reviewer can explicitly reconcile signoff, runtime proof, attempt facts, and command evidence

Required verdict:

- `REVIEW_CONFIRMED_SUCCEEDED`

### E. Disallowed combination

The following combination is not allowed:

```text
NOT_ATTEMPTED + SUCCEEDED
```

It is also not acceptable to leave attempt status unspecified.

## 7. Final reviewer verdict rules

The final reviewer verdict should not be a free-form summary only.
It should map cleanly to the normalized labels above.

### `REVIEW_CONFIRMED_BLOCKED`

Use when:

- the bounded stop is supported by evidence
- the review stack is coherent
- the project correctly did not overclaim success

### `REVIEW_CONFIRMED_FAILED`

Use when:

- the attempt reached a failed reviewed outcome
- failure evidence is clearer than the blocked interpretation
- the stack is still reviewable even though the outcome is negative

### `REVIEW_CONFIRMED_SUCCEEDED`

Use when:

- the bounded first controlled send is positively supported as succeeded
- key evidence fields are present and coherent

### `REVIEW_INCOMPLETE`

Use when:

- the likely posture is still `BLOCKED`
- but one or more required evidence fields remain missing

### `REVIEW_CONTRADICTED`

Use when:

- the review inputs cannot be reconciled safely
- the project should not claim a clean blocked, failed, or succeeded interpretation yet

## 8. Minimum schema template

Use this baseline structure:

```text
classification_id:
review_date:
operator:
final_reviewer:

canonical_path:
execution_mode:
attempt_status:
final_outcome_class:
external_request_started:
external_order_id_state:
final_reviewer_verdict:

signoff_record_ref:
window_open_record_ref:
runtime_verification_record_ref:
attempt_record_ref:
final_review_closeout_ref:
review_artifact_ref:

command_id:
command_detail_ref:
external_order_id:
runtime_window_proof_ref:

command_id_requirement: required|optional
runtime_window_proof_requirement: required|optional
second_request_allowed:
live_trading:
notes:
```

## 9. Stable policy rules

The following rules are fixed for this schema:

- canonical path must remain `ORDER`
- `execution_mode` must remain `testnet`
- `live_trading` remains `NO-GO`
- this schema must not authorize runtime mutation
- this schema must not trigger an external request
- this schema must not replace underlying evidence artifacts

## 10. One-line final interpretation goal

When this schema is used correctly, the project should be able to say, in one bounded sentence:

```text
the first controlled send was [attempted|not_attempted],
the final reviewed outcome was [blocked|failed|succeeded],
external_request_started was [true|false],
external_order_id was [present|absent],
and the final reviewer verdict was [normalized verdict label]
```

That is the classification target this schema exists to standardize.

## 11. Minimal next bounded round

After this schema, the next natural bounded round is:

```text
Real Testnet First Controlled Send Final Review Classification Record V1
```

Scope:

```text
docs-only
apply this schema to one bounded record shape
without adding a new operational layer or changing baseline behavior
```

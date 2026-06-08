# Real testnet review artifact index V1

**Status:** index only - no real key, no external API call, no live trading approval.

**Purpose:** give reviewers one short entrypoint into the `docs/reviews/real_testnet/` directory so they can jump directly to the guidance doc or the synthetic `BLOCKED / PASS / FAIL` examples for the first bounded real external testnet request on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This index is not proof that a real external testnet request has already happened.

## 1. Start here

Read [README.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/README.md) first for:

- what belongs in this directory
- naming rules
- which result label to choose
- secret-handling expectations

## 2. Synthetic examples

Use these as style references only:

- [BLOCKED example](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-23_order-example-blocked.md)
- [PASS example](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-23_order-example-pass.md)
- [FAIL example](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-24_order-example-fail.md)

They demonstrate:

- blocked before external attempt
- accepted and internally consistent
- attempted but not safely explainable

## 3. Actual reviewed artifact

The directory now also contains one non-synthetic first-controlled-send review artifact:

- [FIRST_CONTROLLED_SEND_2026-06-08_order-06b6257f-4003-467c-9e10-ff9085acddd4.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/FIRST_CONTROLLED_SEND_2026-06-08_order-06b6257f-4003-467c-9e10-ff9085acddd4.md)

Use it as the actual bounded-event record for the first successful controlled testnet send, not as a reusable template.

## 4. How to choose the right example

Use:

- `BLOCKED` when the request never should have crossed the external boundary
- `PASS` when the bounded request is reviewable and internally consistent
- `FAIL` when the request crossed the boundary but evidence or behavior became contradictory

## 5. Related upstream docs

For the broader first-real-request stack, also see:

- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_READINESS_BUNDLE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_READINESS_BUNDLE_V1.md)
- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_ENABLEMENT_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_ENABLEMENT_CHECKLIST_V1.md)
- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md)
- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_STORAGE_LOCATION_DECISION_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_STORAGE_LOCATION_DECISION_V1.md)

## 6. Minimal next bounded round

After this index, the next natural bounded round is:

```text
Real Testnet First Real Request Review Artifact Checklist V1
```

Scope:

```text
docs-only
compress the artifact-review steps into one small checklist
for reviewers who only need to validate the record itself
```

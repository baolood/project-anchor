# Real Testnet first real request storage location decision V1

**Status:** storage-location decision only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-23

**Scope:** decide where the future filled signoff record for the first bounded real external testnet request should live, how it should correlate with `command_id` and `/commands/[id]` evidence, and who owns updating it.

Canonical path only:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not create the filled record. It fixes the storage posture before that first record exists.

## 1. Decision

The signoff record template remains in:

- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md)

But the future filled record for the actual first real request should live as a dedicated review artifact under:

```text
docs/reviews/real_testnet/
```

using one file per bounded first-request review event.

This keeps:

- the reusable template separate from the one-time filled record
- the actual signoff artifact inside git-visible review history
- the future `command_id` correlation easy to find

## 2. Why this location is chosen

This location is chosen because the filled record must be:

- easy to find from the docs tree
- easy to review in pull/commit history
- easy to correlate with one concrete `command_id`
- separate from general runbooks and templates
- non-secret by construction

Putting the filled record directly into the template file would mix:

- reusable process definition
- one-time operator evidence

and make later review harder.

## 3. Rejected storage options

These options are rejected for the first real request record:

### A. Only in chat or terminal scrollback

Rejected because:

- not durable enough
- too easy to lose context
- hard to correlate with `command_id`

### B. Inside `/commands/[id]` page only

Rejected because:

- command detail is evidence, not the operator signoff document
- reviewer identity and pre-send signoff text would be too implicit

### C. Overwriting the template doc itself

Rejected because:

- future readers would lose the clean template
- one-time evidence would get mixed with reusable instructions

### D. Repo-external ad hoc file path

Rejected because:

- review visibility would drift
- correlation and retention would become inconsistent

## 4. Naming rule for the filled record

The actual filled record should use a filename shaped like:

```text
docs/reviews/real_testnet/FIRST_REAL_REQUEST_<date>_<command_id>.md
```

Example shape only:

```text
docs/reviews/real_testnet/FIRST_REAL_REQUEST_2026-05-23_order-abc123.md
```

Rules:

- date must be the review date
- `command_id` must be the actual command identifier
- no secrets in filename
- one review event gets one file

## 5. Required correlation fields

The filled record must correlate clearly with `/commands/[id]`.

At minimum it must include:

- `command_id`
- `idempotency_key`
- `host_label`
- `configured_origin`
- `TESTNET_EXECUTOR_MODE`
- final result label
- final command state
- normalized family

This is enough for a reviewer to move between:

```text
docs/reviews/real_testnet/<record>.md
<-> /commands/[id]
<-> event chain
```

without guesswork.

## 6. Ownership rule

The filled record should have clear ownership.

Minimum ownership split:

- operator owns filling runtime posture and command identity
- reviewer owns signoff outcome and result label
- engineering/release lead owns final archival correctness if later edits are required

This prevents the record from becoming “everyone assumed someone else updated it.”

## 7. Update timing rule

The filled record should be updated in two stages:

### Stage 1. Pre-send

Before any first real request attempt:

- fill runtime posture
- fill command identity
- complete pre-send signoff statements
- mark current expected result as pending review

### Stage 2. Post-send

Immediately after review of `/commands/[id]`:

- fill `command_id`
- fill final result label
- fill final command state
- fill normalized family
- fill external request status
- fill whether retreat is required

This keeps pre-send approval and post-send evidence tied together in one artifact.

## 8. Secret-handling rule

The filled record must remain non-secret.

Allowed:

- host label
- configured origin
- key-id-safe confirmation wording
- command metadata
- result/failure family

Not allowed:

- API key
- API secret
- raw auth header
- request signature
- plaintext credential dumps

If secret material appears, the record is invalid and must not be treated as final signoff evidence.

## 9. Relationship to existing bundle

This decision sits after:

- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_READINESS_BUNDLE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_READINESS_BUNDLE_V1.md)
- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_ENABLEMENT_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_ENABLEMENT_CHECKLIST_V1.md)
- [docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_OPERATOR_SIGNOFF_RECORD_V1.md)

Meaning:

- bundle = what to read
- checklist = what to confirm
- signoff record template = what fields exist
- this document = where the actual filled evidence should live

## 10. Minimal next bounded round

After this storage decision, the next natural bounded round is:

```text
Real Testnet First Real Request Review Artifact Example V1
```

Scope:

```text
docs-only
add one synthetic example artifact under docs/reviews/real_testnet/
showing how a BLOCKED or PASS record should look without using real credentials
```

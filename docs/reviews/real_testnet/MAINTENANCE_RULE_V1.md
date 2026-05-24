# Real testnet review artifact maintenance rule V1

**Status:** maintenance rule only - no real key, no external API call, no live trading approval.

**Purpose:** define how files inside `docs/reviews/real_testnet/` should be maintained in the future, without blurring the boundaries between reusable guidance, synthetic examples, and actual filled review artifacts for the first bounded real external testnet request on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This rule governs the documentation bundle only. It does not approve real testnet or live trading.

## 1. Decision

Everything inside `docs/reviews/real_testnet/` must belong to one of exactly three classes:

1. guidance docs
2. synthetic examples
3. actual filled review artifacts

Those classes must not be mixed inside one file.

If a future change makes a file ambiguous about which class it belongs to, that change should be treated as:

```text
FAIL - maintenance boundary blurred
```

## 2. File classes

### A. Guidance docs

These are reusable process documents such as:

- `README.md`
- `INDEX.md`
- `BUNDLE_INDEX_V1.md`
- `ARTIFACT_CHECKLIST_V1.md`
- `REVIEWER_NOTES_RUBRIC_V1.md`

Purpose:

- explain how to use the mini-bundle
- explain naming or review rules
- explain how to judge an artifact

They must remain generic and reusable.

### B. Synthetic examples

These are example artifacts such as:

- `...order-example-blocked.md`
- `...order-example-pass.md`
- `...order-example-fail.md`

Purpose:

- demonstrate format
- demonstrate label semantics
- demonstrate writing style

They must remain obviously synthetic.

### C. Actual filled review artifacts

These are future real review records associated with an actual bounded request.

Purpose:

- capture one concrete review event
- correlate with one real `command_id`
- preserve reviewer/operator signoff

They must remain event-specific and must not become generic instruction docs.

## 3. Update rules by class

### Guidance docs

Allowed changes:

- clarify wording
- add cross-links
- improve structure
- tighten rules

Not allowed:

- inserting one-off runtime evidence
- embedding actual filled record data
- mixing synthetic and real event details into reusable guidance

### Synthetic examples

Allowed changes:

- improve clarity
- align with updated naming or artifact rules
- expand explanation of why a label is `BLOCKED`, `PASS`, or `FAIL`

Not allowed:

- pretending to be real evidence
- using actual secrets
- using actual unredacted production/testnet credentials

### Actual filled review artifacts

Allowed changes:

- fix non-semantic typos
- add missing correlation fields
- append follow-up reviewer clarification

Not allowed:

- rewriting history so the original result label becomes misleading
- removing evidence of anomaly to make a record look cleaner
- turning one event record into a reusable template

## 4. Synthetic vs real distinction rule

Every synthetic example must state clearly that it is synthetic.

Every actual filled artifact must be identifiable as real review evidence through:

- real `command_id`
- actual review date
- actual operator/reviewer identity

If a reader cannot tell whether a file is synthetic or real within a few lines, the file should be fixed immediately.

## 5. Naming discipline

Guidance docs should have stable descriptive names, such as:

- `README.md`
- `INDEX.md`
- `..._V1.md`

Synthetic examples should include obvious synthetic markers, such as:

- `order-example-blocked`
- `order-example-pass`
- `order-example-fail`

Actual filled artifacts should include actual event identity, such as:

- review date
- real `command_id`

This prevents accidental mixing of training/example files with true evidence records.

## 6. Edit review questions

Before editing any file in this directory, answer:

1. Is this file guidance, synthetic, or actual evidence?
2. Does the proposed edit preserve that class?
3. Could this edit make a reader confuse example material with actual review evidence?
4. Does the edit preserve non-secret posture?
5. Does the edit preserve `BLOCKED / PASS / FAIL` label clarity?

If any answer is unclear, the edit should stop until the class boundary is clear.

## 7. No-secret maintenance rule

No class in this directory may contain:

- API key
- API secret
- raw auth header
- request signature
- plaintext credential dumps

If sensitive data appears, the fix is not "leave it because history matters".
The artifact must be treated as invalid documentation and corrected immediately under the repository's secret-handling discipline.

## 8. Relationship to larger docs

This maintenance rule sits below the broader first-real-request stack and only governs this mini-bundle.

It does not replace:

- readiness review
- enablement checklist
- signoff template
- storage decision

It only keeps the artifact-review subdirectory clean and understandable over time.

## 9. Minimal next bounded round

After this maintenance rule, the next natural bounded round is:

```text
Real Testnet Review Artifact Change Log Rule V1
```

Scope:

```text
docs-only
define when edits to guidance docs, synthetic examples,
or actual filled artifacts should also leave a small change-note trail
```

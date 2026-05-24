# Real testnet review artifact change log rule V1

**Status:** change-log rule only - no real key, no external API call, no live trading approval.

**Purpose:** define when edits inside `docs/reviews/real_testnet/` should also leave a small change-note trail, so later reviewers can understand why guidance docs, synthetic examples, or actual filled review artifacts were adjusted.

Canonical path only:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This rule governs documentation maintenance only. It does not authorize real testnet or live trading.

## 1. Decision

Not every typo requires a separate change note, but not every edit should be silent either.

This directory should leave an explicit small change-note trail when a change could alter:

- interpretation
- result-label meaning
- example semantics
- trust in a filled artifact

If a change could affect reviewer understanding and no note is left, the maintenance quality is insufficient.

## 2. When a change note is required

A small change note is required when the edit does any of the following:

- changes label guidance for `BLOCKED`, `PASS`, or `FAIL`
- changes naming rules or storage rules
- changes synthetic example semantics
- changes what the artifact checklist considers acceptable
- changes notes-rubric expectations
- changes a filled artifact beyond non-semantic typo correction

In short:

```text
if the meaning changes, leave a note
```

## 3. When a change note is not required

A separate change note is not required for:

- obvious spelling fixes
- punctuation cleanup
- formatting-only edits
- link target corrections that do not change meaning

These may still be mentioned in normal commit history, but do not need extra artifact-level explanation.

## 4. Where the change note should live

For this mini-bundle, the change note may live in one of two places:

### A. Commit message only

Acceptable for:

- small guidance clarifications
- simple synthetic-example wording fixes

### B. In-file note or appended clarification

Preferred when:

- a filled artifact changes after initial review
- a synthetic example changes label semantics
- a guidance doc changes a review rule materially

The goal is that a later reader does not need to reconstruct intent entirely from git history alone.

## 5. Rules by file class

### Guidance docs

Leave a change note when:

- review rules are tightened or relaxed
- reading order changes significantly
- artifact validation criteria change

### Synthetic examples

Leave a change note when:

- the meaning of the example changes
- the label changes
- the example now demonstrates a different contradiction or success condition

### Actual filled artifacts

Leave a change note when:

- post-review clarification is appended
- a missing correlation field is added after the fact
- an ambiguity is corrected for later readers

Do not silently rewrite a filled artifact in a way that changes what happened.

## 6. Minimum shape of a change note

The change note can stay short. It should answer:

- what changed
- why it changed
- whether the meaning changed

Example shape:

```text
Change note:
- clarified PASS wording to emphasize internal consistency
- no runtime evidence changed
```

Short is fine. Ambiguous is not.

## 7. Anti-patterns

These are not acceptable:

- silently changing a synthetic `FAIL` example so it now looks like `PASS`
- silently changing a filled artifact's conclusion
- tightening the checklist without any note that the standard changed
- replacing a meaningful note with "cleanup" when the interpretation actually changed

If interpretation changed, the documentation should admit that interpretation changed.

## 8. Relationship to maintenance rule

This document extends:

- [MAINTENANCE_RULE_V1.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/MAINTENANCE_RULE_V1.md)

Meaning:

- maintenance rule says what class each file belongs to
- change-log rule says when class-preserving edits still need explicit change context

## 9. Minimal next bounded round

After this change-log rule, the next natural bounded round is:

```text
Real Testnet Review Artifact Completed Mini Bundle V1
```

Scope:

```text
docs-only
add one short closeout doc that states the mini-bundle is now complete,
lists its files, and defines the next likely transition out of docs-only work
```

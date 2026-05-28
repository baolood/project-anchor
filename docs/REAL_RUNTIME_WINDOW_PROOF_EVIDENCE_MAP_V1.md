# Real Runtime Window Proof Evidence Map V1

**Status:** evidence-map only - docs-only, no baseline change, no runtime mutation, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-28**

**Scope:** map each required runtime-window proof item to its expected collection surface, retention location, and review owner for the first controlled real external testnet send.

This document does not authorize a send.
It does not define a new operational layer.
It only answers where each proof item should come from, where it should live, and who is responsible for confirming it.

## 1. Decision

The blocker is no longer vague.
The project already knows that runtime-window proof requires three proof families:

1. cloud-host evidence
2. `/commands/[id]` evidence
3. cross-source reconciliation evidence

The next useful step is therefore one evidence map that answers:

```text
for each required proof item,
where should it be collected,
where should it be retained,
and who is responsible for confirming it?
```

Without this map, the team can name the missing evidence but still lose time deciding where to look or where to store it.

## 2. Evidence-map rules

This map must obey these rules:

1. Every required proof item must have one primary collection surface.
2. Every required proof item must have one expected retention location.
3. Every required proof item must have one review owner.
4. If a proof item is not collectible from the designated surface, it should be treated as `NOT_COLLECTED`, not guessed.
5. Live trading remains `NO-GO`.

## 3. Evidence families

### A. Cloud-host proof

Proof of what the controlled host actually looked like during the bounded real runtime window.

### B. `/commands/[id]` proof

Proof of what the canonical command-detail surface actually showed for the bounded event.

### C. Reconciliation proof

Proof that the host-side and command-side evidence describe the same bounded first controlled send event.

## 4. Evidence map

### A. Cloud-host runtime identity proof

**Proof items:**
- host identity
- revision identity
- runtime window open reference
- runtime posture label

**Primary collection surface:**
- cloud host runtime verification step
- operator-controlled host-side review session

**Expected retention location:**
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_V1.md`
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_V1.md`
- final review artifact under `docs/reviews/real_testnet/`

**Review owner:**
- operator captures
- reviewer confirms

**Blocking if missing:**
- yes

### B. Cloud-host mode and safety proof

**Proof items:**
- `TESTNET_EXECUTOR_MODE`
- `TESTNET_EXECUTOR_REAL_ENABLE`
- configured origin
- host label / venue mapping
- kill switch state
- credential presence confirmed without exposing secrets

**Primary collection surface:**
- cloud host runtime verification step
- controlled host-side inspection

**Expected retention location:**
- `docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md`
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_V1.md`
- final review artifact under `docs/reviews/real_testnet/`

**Review owner:**
- operator captures
- reviewer confirms

**Blocking if missing:**
- yes

### C. Cloud-host review-surface reachability proof

**Proof items:**
- `/ops` reachable
- `/commands` reachable
- `/commands/[id]` reachable when command id exists

**Primary collection surface:**
- cloud host runtime verification step
- bounded runtime-window observation

**Expected retention location:**
- `docs/CLOUD_HOST_RUNTIME_VERIFICATION_CHECKLIST_V1.md`
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_V1.md`
- final review artifact under `docs/reviews/real_testnet/`

**Review owner:**
- operator captures
- reviewer confirms

**Blocking if missing:**
- yes

### D. Command-detail proof

**Proof items:**
- `command_id`
- final command state
- event family
- normalized family
- external request status
- visible external order id, if any

**Primary collection surface:**
- `/ops -> /commands -> /commands/[id]`

**Expected retention location:**
- `docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md`
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_ATTEMPT_RECORD_V1.md`
- final review artifact under `docs/reviews/real_testnet/`
- final classification record / fill trial when applicable

**Review owner:**
- reviewer captures
- operator confirms context

**Blocking if missing:**
- yes, when a real command object should exist

### E. External request / external order identity proof

**Proof items:**
- whether any external request actually started
- whether any external order id was actually present

**Primary collection surface:**
- `/commands/[id]`
- bounded command-detail review

**Expected retention location:**
- `docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md`
- `docs/FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLASSIFICATION_RECORD_V1.md`
- final review artifact under `docs/reviews/real_testnet/`

**Review owner:**
- reviewer captures
- operator confirms no contradiction with host-side observation

**Blocking if missing:**
- yes, if the review stack claims a real attempted command path

### F. Reconciliation proof

**Proof items:**
- host-side window identity matches command-side event identity
- operator and reviewer identities match across records
- timing does not contradict
- runtime posture does not contradict command outcome
- no second request / quick retry escaped the bounded event

**Primary collection surface:**
- final review closeout step
- final review classification record fill
- human comparison across host-side and command-side artifacts

**Expected retention location:**
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLOSEOUT_V1.md`
- `docs/FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLASSIFICATION_RECORD_V1.md`
- final review artifact under `docs/reviews/real_testnet/`

**Review owner:**
- final reviewer

**Blocking if missing:**
- yes

## 5. Retention expectations by surface

### A. Runtime verification and window records

These should retain the host-side facts:

- window identity
- host identity
- revision identity
- runtime posture
- review-surface reachability
- safety toggles and kill switch posture

### B. Execution and attempt records

These should retain the bounded event facts:

- request attempted or blocked
- command linkage
- first visible outcome
- retreat posture
- close posture

### C. Final review artifact

This should retain the fully reviewed interpretation:

- host-side proof summary
- `/commands/[id]` proof summary
- reconciliation result
- final verdict
- whether any second request remains blocked

## 6. Ownership model

Use this simple owner split.

### Operator owns

- host-side capture
- runtime posture observation
- immediate window facts
- retreat readiness and bounded action context

### Reviewer owns

- `/commands/[id]` evidence capture
- event-family interpretation
- normalized-family interpretation
- external request / order-identity interpretation

### Final reviewer owns

- reconciliation across all sources
- final contradiction check
- final verdict
- second-request posture

## 7. Missing-evidence handling rule

If a proof item cannot be collected from its designated surface, it should be marked:

```text
NOT_COLLECTED
```

It should not be backfilled from memory or implied from adjacent fields.

If a proof item is explicitly absent by review, it should be marked:

```text
ABSENT_BY_REVIEW
```

This is especially important for:

- `external_order_id`
- `command_id` when optional
- any proof item that could otherwise be guessed from narrative context

## 8. Current map verdict

The current evidence-map verdict is:

```text
READY TO COLLECT, NOT YET COLLECTED
```

Meaning:

- the project now knows where each proof item should come from
- the project now knows where each proof item should be retained
- the project now knows who should confirm each proof item
- the real proof itself still does not exist yet

## 9. Stable status statement

At this point the correct runtime-window-proof evidence-map summary is:

```text
the project now has a source-of-truth map for runtime-window proof
cloud-host evidence, /commands/[id] evidence, and reconciliation evidence
all have explicit collection surfaces, retention locations, and owners
until those proofs are actually collected, first controlled send remains BLOCKED
live trading: NO-GO
```

## 10. Minimal next bounded round

After this evidence map, the next natural bounded round is:

```text
Real Runtime Window Proof Collection Packet V1
```

Scope:

```text
docs-only
package the exact proof items that would need to be collected in one bounded
runtime window without yet attempting the real request
```

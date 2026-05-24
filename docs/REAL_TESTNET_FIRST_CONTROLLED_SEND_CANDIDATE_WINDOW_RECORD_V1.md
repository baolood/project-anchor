# Real Testnet first controlled send candidate window record V1

**Status:** candidate-window record only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the short record that should exist once the project names a concrete candidate window for the first controlled real external testnet send on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not open the window by itself.
It standardizes the short record that should capture the first moment when the project moves from “scheduling is possible” to “this is the candidate window we may actually use.”

## 1. Decision

Once the project names a concrete candidate window for the first controlled send, that moment should leave a short durable record.

That record should answer:

```text
which host/window is being considered,
who is assigned,
what posture is expected,
and whether the candidate window is still only a candidate
or already blocked
```

If that record is missing, later review has to reconstruct how the first candidate window emerged.

## 2. Fixed applicability

This candidate-window record applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be reused for:

- legacy `QUOTE + BINANCE_TESTNET`
- mocked executor windows
- dry-run windows
- live trading windows

## 3. What this record is for

This record exists to answer one narrow question:

```text
once the project identifies a real candidate window
for the first controlled send,
what exact minimal facts should be frozen before the window is opened
```

It is not:

- the schedule packet itself
- the runtime-window execution record
- the final post-send review closeout

It is the small bridge from “scheduled in principle” to “candidate execution window identified.”

## 4. Required source inputs

This record should be written from bounded source materials:

1. schedule packet  
   [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULE_PACKET_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULE_PACKET_V1.md)
2. scheduling decision record  
   [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md)
3. runtime window spec  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md)

If these are not enough to describe the candidate window clearly, then the candidate is not ready to be named.

## 5. Required record sections

Every candidate-window record should contain all of these sections.

### A. Identity

- candidate window record id
- recorded timestamp
- operator
- reviewer
- optional witness

### B. Candidate window facts

- host identity
- expected revision identity
- candidate window id
- proposed open time
- proposed close expectation
- runtime posture label

### C. Command linkage

- canonical path confirmed: yes/no
- idempotency key
- source
- created_by
- market
- symbol
- side
- notional
- order_type
- stop_price

### D. Readiness linkage

- readiness review reference
- scheduling decision record reference
- schedule packet reference

### E. Candidate status

- candidate status label
- still blocked pending final confirmation: yes/no
- notes

## 6. Minimum candidate-window template

Use this baseline structure:

```text
candidate_window_record_id:
recorded_at:
operator:
reviewer:
witness:

host_identity:
expected_revision_identity:
candidate_window_id:
proposed_open_time:
proposed_close_expectation:
runtime_posture_label:

canonical_path_confirmed:
idempotency_key:
source:
created_by:
market:
symbol:
side:
notional:
order_type:
stop_price:

readiness_review_ref:
scheduling_decision_record_ref:
schedule_packet_ref:

candidate_status_label:
still_blocked_pending_final_confirmation:
notes:
```

## 7. Candidate status labels

Use exactly one label:

### `CANDIDATE_IDENTIFIED`

Use if:

- the project has named one concrete candidate window
- the candidate is bounded and reviewable
- the send has not yet been executed

### `CANDIDATE_BLOCKED`

Use if:

- a concrete candidate window was considered
- but it should not be opened as currently defined

### `INVALID`

Use only if:

- the record later proves inconsistent with the schedule packet
- or the candidate window was named without bounded source materials

## 8. Stable status statement

At this point the correct candidate-window summary is:

```text
once a real candidate window is named for the first controlled send,
the project should leave a short record freezing host, window, posture,
command linkage, and current candidate status
```

## 9. Minimal next bounded round

After this candidate-window record, the next natural bounded round is:

```text
Real Testnet First Controlled Send Candidate Window Closeout V1
```

Scope:

```text
docs-only
record that the candidate-window recording layer is now complete,
and state exactly what still separates a named candidate from an opened real window
```

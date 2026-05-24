# Real Testnet first controlled send scheduling decision record V1

**Status:** scheduling decision record only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the exact short record that should capture who made the final schedule-or-block decision for the first controlled real external testnet send on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not schedule the send by itself.
It standardizes the final administrative record that should exist once the readiness review lands on either `PASS` or `BLOCKED`.

## 1. Decision

The project should not rely on chat history or terminal scrollback to explain who made the final decision to schedule or block the first controlled send.

That decision should leave one short durable record answering:

```text
who decided,
when they decided,
what bounded materials they relied on,
and whether the first controlled send was allowed to be scheduled
```

If that record is missing, later review has to reconstruct too much from memory.

## 2. Fixed applicability

This decision record applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be reused for:

- legacy `QUOTE + BINANCE_TESTNET`
- mocked executor review
- dry-run approval
- live trading approval

## 3. What this record is for

This record exists to answer one narrow question:

```text
after the final readiness review,
did the project schedule the first controlled send,
or correctly keep it blocked
```

It is not:

- the runtime-window execution record
- the signoff artifact for the real attempt itself
- the final review closeout after a real send
- a substitute for the readiness review

It is the short managerial bridge between readiness review and actual scheduling.

## 4. Required source inputs

This record should be written from bounded source materials:

1. readiness review  
   [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md)
2. scheduling decision gate  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_DECISION_GATE_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_DECISION_GATE_V1.md)
3. scheduling packet  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_PACKET_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_SCHEDULING_PACKET_V1.md)

If those are not enough to explain the decision, then the decision should probably still be `BLOCKED`.

## 5. Required record sections

Every scheduling decision record should contain all of these sections.

### A. Identity

- decision record id
- decision date/time
- operator
- reviewer
- optional witness

### B. Scope confirmation

- canonical path confirmed: yes/no
- first controlled send scope confirmed: yes/no
- live trading still `NO-GO`: yes/no

### C. Inputs reviewed

- readiness review reference
- scheduling packet reference
- scheduling gate reference

### D. Final scheduling outcome

- decision label
- first controlled send scheduled: yes/no
- if blocked, blocked reason summary
- if scheduled, bounded send window still required: yes/no

### E. Notes

- short justification
- any follow-up action

## 6. Minimum decision-record template

Use this baseline structure:

```text
decision_record_id:
decision_timestamp:
operator:
reviewer:
witness:

canonical_path_confirmed:
first_controlled_send_scope_confirmed:
live_trading_still_no_go:

readiness_review_ref:
scheduling_packet_ref:
scheduling_gate_ref:

decision_label:
first_controlled_send_scheduled:
blocked_reason_summary:
bounded_send_window_still_required:

notes:
follow_up_action:
```

## 7. Decision labels

Use exactly one label:

### `SCHEDULED`

Use only if:

- readiness review landed `PASS`
- scheduling gate supports window opening
- one bounded first controlled send is allowed to be scheduled
- live trading remains `NO-GO`

### `BLOCKED`

Use if:

- readiness review landed `BLOCKED`
- scheduling gate remains closed
- or reviewer chose not to schedule despite documentary completeness

### `INVALID`

Use only if:

- the project later discovers the record contradicted the real readiness state
- or scheduling happened without the bounded source materials above

## 8. Stable status statement

At this point the correct scheduling-decision-record summary is:

```text
the project should leave one short durable record
for whether the first controlled send was scheduled or blocked
based on the bounded readiness review stack
```

## 9. Minimal next bounded round

After this decision record, the next natural bounded round is:

```text
Real Testnet First Controlled Send Decision Bundle V1
```

Scope:

```text
docs-only
collect readiness review and scheduling decision record
into one short pre-scheduling decision bundle
```

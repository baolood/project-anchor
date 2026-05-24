# Real Testnet first controlled send schedule packet V1

**Status:** schedule packet only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the exact bounded packet that should exist once the project is actually ready to schedule the first controlled real external testnet send on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not schedule the send by itself.
It standardizes what the concrete schedule packet should contain once the project moves from documentary readiness into an actual planned first controlled send.

## 1. Decision

Once the project decides it is ready to schedule the first controlled send, it should not do so from a generic note or implicit memory of “the command we discussed.”

It should schedule the send from one bounded packet that answers:

```text
what exact send is being scheduled,
on which host and posture,
for which bounded window,
under whose ownership,
with which retreat and review expectations
```

If that packet is incomplete, scheduling should stay blocked.

## 2. Fixed applicability

This packet applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be reused for:

- legacy `QUOTE + BINANCE_TESTNET`
- mocked or dry-run scheduling
- live trading

## 3. What this packet is for

This packet exists to answer one narrow question:

```text
if the project is going to actually schedule the first controlled send,
what exact bounded information must be present before the window is opened
```

It is not:

- the runtime-window execution record
- the final review closeout
- the post-send artifact
- a replacement for the readiness review or scheduling decision record

It is the operational packet that exists after “ready to schedule” and before “window opened.”

## 4. Required source inputs

This schedule packet should be built from bounded upstream materials:

1. readiness review  
   [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_READINESS_REVIEW_V1.md)
2. scheduling decision record  
   [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_SCHEDULING_DECISION_RECORD_V1.md)
3. execution record template  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md)

If those are not enough to build a clear packet, the send is probably not actually ready to be scheduled.

## 5. Required packet sections

Every first-controlled-send schedule packet should contain all of these sections.

### A. Identity

- schedule packet id
- preparation timestamp
- operator
- reviewer
- optional witness

### B. Host and window

- host identity
- expected revision identity
- runtime posture label
- intended window id
- planned open time
- planned close expectation

### C. Canonical command summary

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

### D. Runtime safety summary

- `TESTNET_EXECUTOR_MODE` value
- `TESTNET_EXECUTOR_REAL_ENABLE` value
- host/origin confirmed: yes/no
- canonical env family confirmed: yes/no
- credential presence confirmed: yes/no
- kill switch visibility confirmed: yes/no
- ingress freeze intact: yes/no

### E. Review and retreat summary

- `/ops` reachable: yes/no
- `/commands` reachable: yes/no
- `/commands/[id]` reachable: yes/no
- logs supporting only: yes/no
- retreat posture label
- no quick retry rule confirmed: yes/no
- second send not preauthorized: yes/no

### F. Linkage

- readiness review reference
- scheduling decision record reference
- execution record template reference

## 6. Minimum schedule-packet template

Use this baseline structure:

```text
schedule_packet_id:
prepared_at:
operator:
reviewer:
witness:

host_identity:
expected_revision_identity:
runtime_posture_label:
window_id:
planned_open_time:
planned_close_expectation:

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

executor_mode_value:
real_enable_value:
host_origin_confirmed:
canonical_env_family_confirmed:
credential_presence_confirmed:
kill_switch_visibility_confirmed:
ingress_freeze_intact:

ops_reachable:
commands_reachable:
command_detail_reachable:
logs_supporting_only:
retreat_posture_label:
no_quick_retry_rule_confirmed:
second_send_not_preauthorized:

readiness_review_ref:
scheduling_decision_record_ref:
execution_record_template_ref:
```

## 7. Packet quality rules

This packet is valid only if:

- it describes one actual bounded send, not a family of possible sends
- it contains no secret material
- it can be reviewed quickly before the window opens
- it keeps send ownership, review ownership, and retreat ownership explicit

If the packet is too vague to run or too broad to review, it is the wrong packet.

## 8. Stable status statement

At this point the correct schedule-packet summary is:

```text
once the project is truly ready to schedule the first controlled send,
it should prepare one bounded packet that names the exact host, window,
canonical command, runtime posture, and retreat/review expectations
```

## 9. Minimal next bounded round

After this packet, the next natural bounded round is:

```text
Real Testnet First Controlled Send Schedule Packet Closeout V1
```

Scope:

```text
docs-only
record that the actual schedule-packet template is now complete,
and state exactly what still separates packet readiness from the real first controlled send
```

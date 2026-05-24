# Real Testnet first real request scheduling packet V1

**Status:** scheduling packet only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the exact bounded packet that should be handed to the reviewer immediately before deciding whether the first real external testnet request may be scheduled on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize the request by itself.
It defines the exact packet that must be complete, coherent, and reviewable before the runtime window may be opened.

## 1. Decision

The first real testnet request should not be scheduled from memory, chat context, or “we already know the state.”

It should be scheduled only from one bounded packet that answers:

```text
what is being attempted,
under what posture,
with what evidence,
under whose approval,
and with what stop/retreat expectations
```

If that packet is incomplete, result is:

```text
BLOCKED - do not schedule the first real request window
```

## 2. Fixed applicability

This packet applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be used for:

- legacy `QUOTE + BINANCE_TESTNET`
- `TESTNET_EXECUTOR_STUB`
- mocked external executor as if it were real-send proof
- live trading

## 3. Packet objective

The scheduling packet exists to answer one narrow question:

```text
is the project ready to open one bounded real-attempt runtime window,
for one canonical request,
with one reviewer-readable evidence path,
and one immediate retreat posture
```

It is not:

- a general readiness essay
- a place to invent new checklists
- a substitute for the actual runtime-window execution record
- a way to approve multiple commands at once

## 4. Required packet sections

The scheduling packet must contain all of these sections.

### A. Identity and scope

- packet id
- preparation date
- operator
- reviewer
- optional witness
- target host identity
- expected revision identity
- explicit statement that the request is:
  - bounded
  - canonical
  - testnet only
  - not live

### B. Canonical-path confirmation

- canonical path statement:
  - `ORDER + execution_mode=testnet`
- explicit statement that legacy `QUOTE + BINANCE_TESTNET` is not in use
- explicit statement that `TESTNET_EXECUTOR_STUB` is not valid proof for this attempt
- explicit statement that the request is a first real testnet attempt, not a dry-run or mock-only review

### C. Runtime posture summary

- current `TESTNET_EXECUTOR_MODE`
- current `TESTNET_EXECUTOR_REAL_ENABLE` posture
- runtime posture label:
  - `mock`
  - `real-but-disabled`
  - `real-enabled-for-bounded-window`
- explicit retreat posture:
  - `mock`
  - fail-closed
- explicit statement that ingress/domain posture remains frozen

### D. Safety and host summary

- host safety confirmed
- exact HTTPS origin confirmed
- host label confirmed
- canonical env family confirmed as `TESTNET_EXCHANGE_*`
- credential presence confirmed without exposing values
- merged kill switch visibility confirmed

### E. Review-surface summary

- `/ops` reachable enough for review
- `/commands` reachable enough for locate-and-verify
- `/commands/[id]` reachable enough for final evidence review
- logs treated as supporting evidence only

### F. Planned command summary

- one-command-only statement
- one idempotency key
- one source
- one created_by
- market
- symbol
- side
- intentionally small notional
- order_type
- positive stop_price
- no automatic retry
- second attempt not preauthorized

### G. Linked prerequisite evidence

The packet must explicitly link to:

1. controlled-attempt prereq check  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_CONTROLLED_ATTEMPT_PREREQ_CHECK_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_CONTROLLED_ATTEMPT_PREREQ_CHECK_V1.md)
2. runtime window spec  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_RUNTIME_WINDOW_SPEC_V1.md)
3. dry activation drill  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_DRY_ACTIVATION_DRILL_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_DRY_ACTIVATION_DRILL_V1.md)
4. execution record  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md)
5. review closeout  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_REVIEW_CLOSEOUT_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_REVIEW_CLOSEOUT_V1.md)
6. evidence-bundle index  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_EVIDENCE_BUNDLE_INDEX_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EVIDENCE_BUNDLE_INDEX_V1.md)
7. review artifact home  
   [docs/reviews/real_testnet/README.md](/Users/baolood/Projects/project-anchor/docs/reviews/real_testnet/README.md)

### H. Explicit reviewer decision block

The packet must end with a small decision block:

- `PASS - scheduling allowed`
- `BLOCKED - scheduling not allowed`
- reviewer notes
- date/time of decision

## 5. Minimum scheduling packet template

Use this baseline structure:

```text
packet_id:
preparation_date:
operator:
reviewer:
witness:

target_host_identity:
expected_revision_identity:
bounded_attempt_statement:
testnet_only_statement:
live_trading_still_no_go: yes/no

canonical_path_confirmed: yes/no
legacy_path_not_used: yes/no
stub_not_used_as_proof: yes/no

executor_mode_value:
real_enable_value:
runtime_posture_label:
retreat_posture_label:
ingress_freeze_intact: yes/no
domain_work_deferred: yes/no

host_safety_confirmed: yes/no
exact_origin_confirmed: yes/no
host_label_confirmed: yes/no
canonical_env_family_confirmed: yes/no
credential_presence_confirmed: yes/no
kill_switch_visibility_confirmed: yes/no

ops_surface_reachable: yes/no
commands_surface_reachable: yes/no
command_detail_surface_reachable: yes/no
logs_supporting_only: yes/no

single_command_only: yes/no
idempotency_key:
source:
created_by:
market:
symbol:
side:
notional:
order_type:
stop_price:
automatic_retry_absent: yes/no
second_attempt_not_preauthorized: yes/no

prereq_check_ref:
runtime_window_ref:
dry_activation_ref:
execution_record_ref:
review_closeout_ref:
evidence_bundle_ref:
review_artifact_home_ref:

reviewer_decision:
reviewer_notes:
decision_timestamp:
```

## 6. Packet quality rules

The scheduling packet is valid only if:

- it fits on one bounded review surface
- it contains no secret material
- it does not require the reviewer to remember unstated context
- it names the exact command posture rather than “roughly this request”
- it keeps sendability weaker than reviewability

If the packet makes the first send easier than the first review, it is the wrong packet.

## 7. PASS criteria

This scheduling packet is `PASS` only if:

- the canonical path is explicit
- runtime posture is explicit
- safety and host posture are explicit
- review surfaces are explicit
- one bounded command is explicit
- linked prerequisite docs are all present
- reviewer can issue a clear `PASS/BLOCKED` scheduling decision
- live trading remains `NO-GO`

## 8. BLOCKED criteria

This scheduling packet is `BLOCKED` if:

- any section is missing
- runtime posture depends on guesswork
- the exact command is not explicit
- the packet silently assumes ingress/domain changes
- the retreat posture is not immediate
- the reviewer would need to reconstruct context from memory

`BLOCKED` here means “not ready to schedule,” not “project failed.”

## 9. Stable status statement

At this point the correct scheduling-packet summary is:

```text
the first real request should be scheduled only from one bounded packet
that unifies posture, command, review surfaces, linked prerequisites,
and a final reviewer scheduling decision
```

## 10. Minimal next bounded round

After this packet, the next natural bounded round is:

```text
Real Testnet First Real Request Scheduling Decision Gate V1
```

Scope:

```text
docs-only
define the exact go/no-go decision rule for when a completed scheduling packet
may actually open the first bounded real-attempt runtime window
```

# Real Runtime Window Proof Collection Packet V1

**Status:** collection-packet only - docs-only, no baseline change, no runtime mutation, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-28**

**Scope:** package the exact runtime-window proof items that would need to be collected during one bounded real runtime window for the first controlled real external testnet send, without yet attempting the real request.

This document does not authorize the request.
It does not open the window.
It only defines the exact bounded packet of proof items that must be collectible if the runtime window is ever opened.

## 1. Decision

The project now knows:

- what runtime-window proof still requires real evidence
- where each proof item should come from
- where each proof item should be retained
- who should confirm each proof item

The next useful step is therefore one bounded collection packet that says:

```text
if a real runtime window were opened,
what exact proof items must be collected in that window,
in what grouped packet,
by which owner,
and with what fail-closed rule if collection is incomplete?
```

Without this packet, the team can know the theory of missing evidence but still improvise the real collection moment.

## 2. Packet design rules

This packet must obey all of these rules:

1. It must stay bounded to one canonical event.
2. It must be collectible without exposing secrets.
3. It must not assume a second attempt.
4. It must fail closed if required proof items are not collectible.
5. It must preserve `live trading = NO-GO`.
6. It must not authorize the real request by itself.

## 3. Packet objective

The packet exists to answer one narrow question:

```text
if the project opens one real bounded runtime window,
what exact evidence must be collected before the final review
can move past REVIEW_INCOMPLETE?
```

It is not:

- a send plan
- a deployment checklist
- a generic incident template
- a substitute for `/commands/[id]`

## 4. Packet structure

The collection packet is grouped into three proof blocks.

### Block A. Cloud-host proof packet

Collect all of these during the bounded real runtime window.

**Identity and window facts**
- host identity
- deployed revision identity
- runtime window id
- runtime window open timestamp reference
- operator identity
- reviewer identity

**Runtime posture facts**
- `TESTNET_EXECUTOR_MODE`
- `TESTNET_EXECUTOR_REAL_ENABLE`
- runtime posture label
- configured origin
- host label / venue mapping
- kill switch state
- credential presence confirmed without exposing secrets

**Review-surface reachability facts**
- `/ops` reachable
- `/commands` reachable
- `/commands/[id]` reachable if command id exists

**Retention targets**
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_RECORD_V1.md`
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_RUNTIME_VERIFICATION_RECORD_V1.md`
- final review artifact under `docs/reviews/real_testnet/`

**Primary owner**
- operator captures
- reviewer confirms

**Fail-closed rule**
- if any required item in Block A is not collectible, the packet verdict remains `BLOCKED`

### Block B. Command-detail proof packet

Collect all of these from the canonical command surface if a real command object exists.

**Command identity facts**
- `command_id`
- idempotency key
- source
- created_by

**Outcome facts**
- final command state
- event family
- normalized family
- external request status
- external order id, if present

**Retention targets**
- `docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md`
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_ATTEMPT_RECORD_V1.md`
- final review artifact under `docs/reviews/real_testnet/`
- final classification record when applicable

**Primary owner**
- reviewer captures
- operator confirms bounded context

**Fail-closed rule**
- if a real command object should exist and these fields are not collectible, mark them `NOT_COLLECTED` and keep the packet verdict at `BLOCKED` or `REVIEW_INCOMPLETE`

### Block C. Reconciliation proof packet

Collect the minimum proof that host-side and command-side evidence refer to the same bounded event.

**Reconciliation facts**
- host-side window identity matches command-side event identity
- operator identity is consistent across records
- reviewer identity is consistent across records
- attempt timing does not contradict runtime-window timing
- runtime posture does not contradict command outcome
- no second request or quick retry escaped the bounded event

**Retention targets**
- `docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLOSEOUT_V1.md`
- `docs/FIRST_CONTROLLED_SEND_FINAL_REVIEW_CLASSIFICATION_RECORD_V1.md`
- final review artifact under `docs/reviews/real_testnet/`

**Primary owner**
- final reviewer

**Fail-closed rule**
- if reconciliation is not provable, the packet verdict must remain `BLOCKED` or `REVIEW_CONTRADICTED`

## 5. Minimum collection packet template

Use this baseline structure:

```text
collection_packet_id:
collection_date:
operator:
reviewer:
optional_witness:

canonical_path: ORDER
execution_mode: testnet

block_a_cloud_host_packet:
  host_identity:
  revision_identity:
  runtime_window_id:
  runtime_window_open_ref:
  operator_identity_confirmed:
  reviewer_identity_confirmed:
  executor_mode:
  real_enable:
  runtime_posture_label:
  configured_origin:
  host_label:
  kill_switch_state:
  credential_presence_confirmed:
  ops_reachable:
  commands_reachable:
  command_detail_reachable:

block_b_command_packet:
  command_id:
  idempotency_key:
  source:
  created_by:
  final_command_state:
  event_family:
  normalized_family:
  external_request_status:
  external_order_id:

block_c_reconciliation_packet:
  window_identity_matches_command_event:
  operator_identity_consistent:
  reviewer_identity_consistent:
  timing_consistent:
  runtime_posture_consistent_with_command_outcome:
  no_second_request_escape:

packet_verdict:
missing_items:
notes:
live_trading: NO-GO
```

## 6. Missing-item handling

Use these exact rules.

### A. Missing required item

If a required proof item was expected from a designated surface but cannot be collected, record:

```text
NOT_COLLECTED
```

### B. Explicit absence

If the review conclusion depends on a proven absence, record:

```text
ABSENT_BY_REVIEW
```

### C. Optional item not present

If an item is optional in the bounded event posture and genuinely not present, record:

```text
OPTIONAL_ABSENT
```

## 7. Packet verdict rules

Use only these verdicts.

### `READY_TO_COLLECT`

Use if:

- the packet structure is coherent
- all required proof items have a known source and retention target
- the packet could be used in a real bounded window

This is the correct current documentary verdict.

### `BLOCKED`

Use if:

- any required packet section cannot yet be tied to a real collection surface
- the packet would still force improvisation during the real window

### `INVALID`

Use only if:

- the packet contradicts the evidence map
- the packet weakens fail-closed handling
- the packet implies request authorization or live readiness

## 8. Current packet verdict

The current packet verdict is:

```text
READY_TO_COLLECT
```

Meaning:

- the packet is ready as a bounded collection shape
- the real proof still has not been collected
- the first controlled send remains `BLOCKED` until the packet is populated from real evidence

## 9. Stable status statement

At this point the correct collection-packet summary is:

```text
the project now has a bounded packet of runtime-window proof items
cloud-host, command-detail, and reconciliation evidence can be collected
through one structured packet if a real runtime window is ever opened
until the packet is populated from real evidence, first controlled send remains BLOCKED
live trading: NO-GO
```

## 10. Minimal next bounded round

After this collection packet, the next natural bounded round is:

```text
Real Runtime Window Proof Fill Trial V1
```

Scope:

```text
docs-only
simulate one conservative fill of the collection packet using current documentary
materials only, to expose any remaining collection-shape gaps before real use
```

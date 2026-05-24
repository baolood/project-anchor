# Real Testnet first controlled send window open record V1

**Status:** window-open record only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define the short record that should exist once the first controlled real external testnet send candidate window is actually opened on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize the send by itself.
It standardizes the minimum durable record that should freeze the exact moment when the candidate window transitions from closed to opened.

## 1. Decision

Once the first controlled send candidate window is truly opened, that transition should leave a short durable record.

That record should answer:

```text
which window was opened,
who opened and reviewed it,
what runtime posture was active at open,
and whether the window entered an opened state cleanly or was blocked at the boundary
```

If that record is missing, later review has to reconstruct the start of the real execution window from scattered evidence.

## 2. Fixed applicability

This window-open record applies only to:

```text
ORDER + execution_mode=testnet
```

It must not be reused for:

- legacy `QUOTE + BINANCE_TESTNET`
- mocked executor windows
- dry-run commands
- live trading

## 3. What this record is for

This record exists to answer one narrow question:

```text
once the real candidate window actually opens,
what exact minimal facts should be frozen
before the first controlled send is attempted inside that opened window
```

It is not:

- the candidate-window record
- the final execution record
- the post-send review closeout

It is the short bridge from “window may open” to “window is now open under an explicit posture.”

## 4. Required source inputs

This record should be written from bounded source materials:

1. window-open checklist  
   [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CHECKLIST_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_WINDOW_OPEN_CHECKLIST_V1.md)
2. candidate-window record  
   [docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_CONTROLLED_SEND_CANDIDATE_WINDOW_RECORD_V1.md)
3. runtime execution record template  
   [docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md](/Users/baolood/Projects/project-anchor/docs/REAL_TESTNET_FIRST_REAL_REQUEST_EXECUTION_RECORD_V1.md)

If these are not enough to describe the opened window cleanly, then the window is not ready to be recorded as opened.

## 5. Required record sections

Every window-open record should contain all of these sections.

### A. Identity

- window-open record id
- recorded timestamp
- operator
- reviewer
- optional witness

### B. Opened-window facts

- host identity
- revision identity
- candidate window id
- actual open timestamp
- runtime posture label
- open status label

### C. Runtime posture at open

- `TESTNET_EXECUTOR_MODE`
- `TESTNET_EXECUTOR_REAL_ENABLE`
- host label
- configured origin confirmed: yes/no
- canonical env family confirmed: yes/no
- credential presence confirmed: yes/no
- kill switch visibility confirmed: yes/no

### D. Review-surface confirmation

- `/ops` reachable at open: yes/no
- `/commands` reachable at open: yes/no
- `/commands/[id]` reachable at open: yes/no
- logs supporting-only posture confirmed: yes/no

### E. Command linkage

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

### F. Window-open discipline

- one-command-only rule confirmed: yes/no
- no quick retry rule confirmed: yes/no
- second send preauthorized: yes/no
- retreat immediately available: yes/no
- notes

## 6. Minimum window-open template

Use this baseline structure:

```text
window_open_record_id:
recorded_at:
operator:
reviewer:
witness:

host_identity:
revision_identity:
candidate_window_id:
actual_open_timestamp:
runtime_posture_label:
open_status_label:

executor_mode_value:
real_enable_value:
host_label:
configured_origin_confirmed:
canonical_env_family_confirmed:
credential_presence_confirmed:
kill_switch_visibility_confirmed:

ops_reachable_at_open:
commands_reachable_at_open:
command_detail_reachable_at_open:
logs_supporting_only_confirmed:

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

one_command_only_confirmed:
no_quick_retry_rule_confirmed:
second_send_preauthorized:
retreat_immediately_available:
notes:
```

## 7. Open status labels

Use exactly one label:

### `WINDOW_OPENED`

Use if:

- the candidate window actually transitioned to open
- runtime posture was explicit at the moment of open
- review surfaces remained reachable
- the first controlled send has not yet been replaced by a broader debugging session

### `WINDOW_OPEN_BLOCKED`

Use if:

- the opening moment was reached
- but the window should not be treated as truly opened because posture or reviewability was uncertain

### `INVALID`

Use only if:

- the record later proves inconsistent with the actual runtime posture
- or the window was declared open without bounded source materials

## 8. Stable status statement

At this point the correct window-open-record summary is:

```text
once the first controlled send window actually opens,
the project should leave a short record freezing host, timing,
runtime posture, reviewability, command linkage, and discipline posture
before the first controlled send is attempted
```

## 9. Minimal next bounded round

After this window-open record, the next natural bounded round is:

```text
Real Testnet First Controlled Send Window Open Record Closeout V1
```

Scope:

```text
docs-only
record that the window-open recording layer is now complete,
and state exactly what still separates an opened window
from an actually attempted first controlled send
```

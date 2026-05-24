# Real testnet first real request execution record V1

**Status:** execution-record template only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-24**

**Scope:** define the exact runtime-window execution record that should be filled when the first real external testnet request is actually attempted on the canonical path:

```text
Command.type = ORDER
payload.execution_mode = testnet
```

This document does not authorize the first real request.
It standardizes what must be captured from the runtime window itself once that request is really attempted.

## 1. Decision

The first real request should produce not only a signoff record and `/commands/[id]` evidence, but also one bounded execution record describing what happened inside the runtime window itself.

This record exists because:

- the signoff record captures approval posture
- `/commands/[id]` captures command evidence
- the execution record captures the runtime-window facts that connect the two

If that middle layer is missing, later review has to reconstruct too much from memory.

## 2. What this record is for

This record is meant to answer:

```text
when the window opened,
who participated,
what posture was active,
whether one canonical request was actually attempted,
what the first visible outcome was,
and how the window was closed
```

It is not a general incident report.
It is the narrow runtime-window execution ledger for the first real attempt.

## 3. Fixed applicability

This record is valid only for:

```text
ORDER + execution_mode=testnet
```

It must not be reused for:

- legacy `QUOTE + BINANCE_TESTNET`
- `TESTNET_EXECUTOR_STUB`
- dry-run commands
- live trading

## 4. Required record sections

Every first-real-request execution record should contain all of these sections.

### A. Window identity

- `window_id`
- open timestamp
- close timestamp
- host identity
- revision identity

### B. Participants

- operator
- reviewer
- optional witness / secondary reviewer

### C. Runtime posture at open

- `TESTNET_EXECUTOR_MODE`
- whether real wire was enabled
- runtime posture label
- host label
- configured origin
- kill switch state confirmed: yes/no
- credential presence confirmed: yes/no

### D. Attempt facts

- was one request attempted: yes/no
- command id
- idempotency key
- source
- created_by
- market / symbol / side / notional / order_type / stop_price

### E. First visible outcome

- final command state
- event family classification
- normalized family
- external request status
- retreat required: yes/no

### F. Window close posture

- window closed cleanly: yes/no
- second request attempted: yes/no
- verdict: `PASS / BLOCKED / FAIL`
- notes

## 5. Minimum execution-record template

Use this baseline structure:

```text
window_id:
timestamp_open:
timestamp_close:
host_identity:
revision_identity:

operator:
reviewer:
witness:

executor_mode:
real_wire_enabled:
runtime_posture_label:
host_label:
configured_origin:
kill_switch_state_confirmed:
credential_presence_confirmed:

request_attempted:
command_id:
idempotency_key:
source:
created_by:
market:
symbol:
side:
notional:
order_type:
stop_price:

final_command_state:
event_family:
normalized_family:
external_request_status:
retreat_required:

window_closed_cleanly:
second_request_attempted:
verdict:
notes:
```

## 6. Required note prompts

The `notes` section should answer these in plain language:

- Was the runtime window opened under the expected posture?
- Did the request remain bounded to one canonical attempt?
- What was the first reviewable outcome?
- Was retreat required?
- Was the window closed cleanly, or did ambiguity remain?
- Is any second request still blocked pending follow-up review?

This ensures the record is useful even when the verdict is `BLOCKED` or `FAIL`.

## 7. Relationship to adjacent records

This record is not a replacement for:

- signoff record
- `/commands/[id]` evidence
- review artifact

Instead:

- signoff record explains approval and pre-send posture
- execution record explains what happened in the window
- `/commands/[id]` explains command-level evidence
- review artifact explains the final review conclusion

All four should stay consistent.

## 8. PASS criteria

This execution record template is `PASS` only if it can cleanly capture:

- window open/close
- explicit participants
- runtime posture at open
- one bounded request attempt
- first visible outcome
- retreat and second-attempt posture

## 9. BLOCKED criteria

This execution record template is `BLOCKED` if:

- the runtime window cannot be described as a bounded event
- participants are ambiguous
- runtime posture at open is ambiguous
- first visible outcome cannot be summarized cleanly
- the close posture cannot distinguish “closed” from “left hanging”

That is a signal to tighten the process before the real attempt happens.

## 10. FAIL criteria

This execution record template is `FAIL` if:

- it would allow the first real attempt to proceed without clear runtime-window facts
- it cannot record whether a second request was attempted
- it leaves retreat posture or close state too vague to audit later

## 11. Stable status statement

At this point the correct execution-record summary is:

```text
the first real request should produce a dedicated runtime-window execution record
that bridges signoff posture and command evidence
one bounded attempt, one bounded closeout, and explicit retreat status all matter
live trading: NO-GO
```

## 12. Minimal next bounded round

After this record, the next natural bounded round is:

```text
Real Testnet First Real Request Review Closeout V1
```

Scope:

```text
docs-only
define the final closeout structure that should combine signoff,
execution record, command evidence, and review verdict after the first real request
```

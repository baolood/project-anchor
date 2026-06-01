# Alert Platform Wiring Decision + First Test Alert Plan V1

## Status

- Document type: wiring decision and first test-alert plan only
- Telegram wiring performed by this document: NO
- Telegram secret configured by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Purpose

This document narrows the first Telegram-based alerting step into a bounded,
executable, reviewable plan.

It does **not** perform the wiring.

It answers:

- what Telegram delivery mechanism should be used
- how the secret should be handled
- what the first test alert should look like
- what evidence must be captured
- how to stop safely if the first execution does not behave as expected

## Current prerequisites

The following are already true:

1. **P0/P1 platform selection is complete**
   - **`docs/ALERT_PLATFORM_SELECTION_DECISION_V1.md`** selected Telegram

2. **Wiring is now authorized**
   - **`docs/ALERT_PLATFORM_WIRING_AUTHORIZATION_REVIEW_V1.md`** authorized the
     bounded wiring step

3. **Alert semantics are already fixed**
   - SLI/SLO thresholds exist in **`docs/SERVICE_SLI_SLO.md`**
   - alert thresholds and routing semantics exist in
     **`docs/ALERTING_ROUTING.md`**

4. **Current state is still pre-live**
   - real external request: NOT AUTHORIZED
   - live trading: NO-GO

## Wiring decision

### Chosen Telegram mechanism

The preferred first wiring path is:

- **Telegram bot token + single operator chat target**

This is preferred over a broader multi-recipient or webhook-first path because:

- it is the smallest bounded surface
- it directly supports **P0/P1** operator visibility
- it produces clear delivery and acknowledgement evidence
- it avoids inventing a larger routing topology before the first ack proof

### Secret handling decision

Telegram secret handling must follow these rules:

1. bot token must **not** be stored in the repository
2. bot token must **not** be written into tracked docs
3. bot token must **not** appear in evidence artifacts
4. token should be injected through a host-local operator-managed secret path
5. the repo may record only:
   - where the secret is expected to live
   - who injects it
   - how to verify presence without printing the value

### Repository-visible secret method

The repository-visible method should be recorded only as:

```text
Telegram token source: host-local operator-managed secret
Secret value committed to repo: NO
Secret value copied into evidence artifacts: NO
```

## First test alert plan

### Test target

The first bounded alert test should target:

- one Telegram operator destination for **baolood**

### Test rule scope

The first test should validate only the minimum delivery + ack path needed for
Week 3 closure:

- **one P1-style test alert**

This is enough for the first proof because:

- **P1** already exercises the direct operator delivery path
- it avoids starting with a more disruptive **P0** simulation
- it is sufficient to prove delivery, acknowledgement, and evidence capture

### Test alert message shape

The first test alert should be explicitly marked as a test and include:

- project identifier
- alert rule id
- severity
- UTC timestamp
- clear test marker
- expected ack instruction

Suggested message shape:

```text
[TEST][Project Anchor][P1][AL-AVAIL]
UTC: <timestamp>
Purpose: bounded alert-path verification only
Action: acknowledge receipt and reply with UTC timestamp
```

### Ack capture requirement

The first evidence bundle must include:

- test alert id / rule id
- severity
- delivered target
- delivered at UTC
- operator response
- ack time UTC
- screenshot or copied Telegram message
- copied response text
- linked manual ops log reference

## Evidence location decision

The first test-alert evidence bundle should be recorded under:

- **`artifacts/alerting/`**

Recommended artifact naming pattern:

- **`<UTC timestamp>-telegram-first-test-alert-evidence-bundle.md`**

## Failure stop rule

The first execution must stop immediately if any of the following occur:

1. the secret path is unclear
2. the token cannot be injected without exposing its value
3. the test message would go to the wrong target
4. the test would send outside the intended Telegram operator path
5. the test cannot be clearly marked as a test
6. evidence cannot be captured without leaking secrets

If any stop rule triggers:

- do **not** send the alert
- record the failure reason
- keep Week 3 alerting as **`IN_PROGRESS`**

## Not authorized by this plan

This document does **not** authorize:

- creating the Telegram bot in this document
- storing the Telegram token in the repo
- modifying `.env` in this document
- sending the test alert in this document
- collecting live ack evidence in this document
- wiring additional paging vendors
- changing backend code
- real external request
- live trading

## Recommended next task

- **`Alert Platform First Wiring Execution Authorization Review`**

That task should authorize, for one bounded execution only:

- Telegram secret presence verification
- Telegram bot/chat target configuration
- one test alert send
- one ack evidence bundle collection

## Effect on checklist state

Current effect:

- **`Alert rules + routing implemented`**: remain **`IN_PROGRESS`**
- **`G2 — P0/P1 alerting verified (test alert acked)`**: remain **`NOT DONE`**

This plan narrows the first execution path but does not itself satisfy either
gate.

## Final decision

- Telegram mechanism: bot token + single operator chat target
- Secret method: host-local operator-managed secret, not stored in repo
- First test scope: one bounded P1-style test alert
- Evidence location: **`artifacts/alerting/`**
- Wiring performed by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

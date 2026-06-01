# Alert Platform Selection Decision V1

## Status

- Decision type: platform selection only
- Concrete alerting platform selected: YES
- Live tool wiring performed by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Background

**`docs/ALERT_PLATFORM_SELECTION_AUTHORIZATION_REVIEW_V1.md`** authorized
concrete alerting platform selection.

Current alerting baseline documents:

- **`docs/SERVICE_SLI_SLO.md`**
- **`docs/ALERTING_ROUTING.md`**
- **`docs/SYNTHETIC_CHECKS_CRITICAL_ENDPOINTS_V1.md`**

Current Week 3 alerting state:

- SLI/SLO baseline: defined
- alert rules / routing baseline: defined
- synthetic checks baseline: defined
- first controlled synthetic checks execution: PASS
- concrete alert platform selected before this document: NO
- live tool wiring before this document: NO
- real ack evidence before this document: NO

## Selection question

Which concrete path should Project Anchor use for Week 3 alert routing and
acknowledgement evidence?

## Decision

Selected alerting path:

- P0/P1 paging target: Telegram
- P2/P3 routing path: GitHub issue plus manual ops log
- Ack evidence format: screenshot or copied alert message plus UTC timestamp
  plus operator response

## P0 / P1 target

P0 / P1 alerts should route to Telegram because the current go-live
preparation phase needs fast operator visibility with minimal operational
overhead.

Selected P0 / P1 path:

```text
Telegram alert target
```

This decision does not yet select a bot token, chat ID, webhook, or
implementation mechanism. Those belong to a later wiring task.

## P2 / P3 target

P2 / P3 alerts may use a lighter asynchronous path.

Selected P2 / P3 path:

```text
GitHub issue + manual ops log
```

Rationale:

- lower urgency than P0/P1
- reviewable inside the repo / GitHub workflow
- no need to introduce a second paging platform for non-urgent alerts
- keeps operator evidence simple and auditable

## Ack evidence requirement

A valid ack evidence bundle must include:

- alert id / rule id
- severity
- triggered at UTC
- delivered to
- operator
- ack response
- ack time UTC
- evidence:
  - screenshot OR copied alert message
  - copied operator response
  - link to issue / ops log when applicable

Minimum ack expectations:

- P0: acknowledged within 5 minutes
- P1: acknowledged within 15 minutes
- P2/P3: acknowledged through issue / ops log workflow, timing recorded but
  not treated as paging SLA unless later upgraded

## Current rule mapping

| Rule ID | Severity | Selected route |
|---|---|---|
| **`AL-AVAIL`** | **P1** | Telegram |
| **`AL-ERRORS`** | **P1** | Telegram |
| **`AL-WORKER`** | **P1** | Telegram |
| **`AL-LATENCY`** | **P2** | GitHub issue + manual ops log |

## Not authorized by this decision

This document does **not** authorize:

- creating a Telegram bot
- adding a Telegram token
- storing secrets
- configuring webhooks
- sending a test alert
- wiring live alert rules
- setting up cron / scheduler
- changing backend code
- changing credentials
- changing `.env`
- changing kill switch
- creating domain commands
- real external request
- live trading

## Implementation boundary for the next task

The next valid task is:

- **`Alert Platform Wiring Authorization Review`**

That task must decide whether to authorize:

- Telegram bot / channel setup
- secret handling method
- test alert delivery
- ack evidence collection
- GitHub issue / manual ops log evidence format

No live wiring should happen until that authorization review is complete.

## Done criteria impact

This decision alone does not make **`Alert rules + routing implemented`**
`DONE`.

That row remains `IN_PROGRESS` until all are true:

- concrete tool / target selected: YES
- alert rules wired to selected target: YES
- test alert delivered: YES
- real ack evidence collected: YES
- evidence recorded in repo or linked closeout: YES

Current status after this decision:

- concrete tool / target selected: YES
- alert rules wired: NO
- test alert delivered: NO
- ack evidence collected: NO
- Alert rules + routing implemented: IN_PROGRESS
- G2 — P0/P1 alerting verified: NOT DONE

## Final decision

- P0/P1 alerting platform: Telegram
- P2/P3 routing path: GitHub issue + manual ops log
- Ack evidence format: screenshot or copied message + UTC timestamp + operator
  response
- Live tool wiring performed: NO
- Test alert fired: NO
- Ack evidence collected: NO
- Real external request authorized: NO
- Live trading: NO-GO

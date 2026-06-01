# Alert Platform Wiring Authorization Review V1

## Status

- Review type: wiring authorization review only
- Telegram selected for P0/P1 before this review: YES
- Live Telegram wiring authorized by this review: YES
- Live Telegram wiring performed by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Question under review

Now that the project has:

- selected Telegram for **P0/P1**
- selected GitHub issue + manual ops log for **P2/P3**
- fixed the minimum ack evidence format
- kept Week 3 alerting in **`IN_PROGRESS`**

is it now appropriate to authorize the next bounded step:

- wiring Telegram for **P0/P1**
- defining the secret-handling path
- defining the first test-alert path
- defining the ack-evidence collection path

This review does **not** perform the wiring. It decides only whether wiring is
now authorized and what constraints must apply.

## Current state

The following are already true:

1. **Selection is complete**
   - **`docs/ALERT_PLATFORM_SELECTION_DECISION_V1.md`** fixed:
     - **P0/P1** = Telegram
     - **P2/P3** = GitHub issue + manual ops log
     - ack evidence shape = screenshot or copied message + UTC timestamp +
       operator response

2. **The upstream semantics are already fixed**
   - SLI/SLO targets exist in **`docs/SERVICE_SLI_SLO.md`**
   - alert thresholds and routing intent exist in **`docs/ALERTING_ROUTING.md`**
   - on-call severity and escalation semantics exist in **`docs/ON_CALL_SOP.md`**

3. **The remaining blocker is not semantic**
   - the project no longer lacks rule definitions
   - the project no longer lacks tool selection
   - the project still lacks live tool wiring and ack evidence

## Decision

### Decision result

- Live Telegram wiring now authorized: YES
- Live Telegram wiring performed by this review: NO
- Week 3 alerting row moved to DONE by this review: NO

### Why wiring authorization is now appropriate

Telegram is already chosen as the concrete **P0/P1** path. Continuing to stop
at selection would not reduce uncertainty further.

The next meaningful blocker is operational:

- how the Telegram target is wired
- how the secret is handled
- how a test alert is sent safely
- how the ack trail is collected

Those are exactly the questions a bounded wiring task should answer.

## What the next task is allowed to do

The next task may:

1. define the concrete Telegram delivery target form
   - bot + chat target
   - or another Telegram mechanism with equivalent delivery behavior
2. define the secret handling path
3. define the bounded test-alert firing method
4. define the ack evidence capture steps
5. define the evidence record location for the alert test closeout

## Secret handling constraints

The next task may authorize only a bounded secret path. Minimum rules:

1. do **not** commit Telegram secrets to the repo
2. do **not** store secrets in tracked docs
3. do **not** place secrets in long-lived plaintext evidence artifacts
4. prefer environment-based or host-local secret injection with a separately
   documented operator step
5. record only the secret **location / method**, never the secret value

## Test alert constraints

The next task may authorize one bounded test alert path only if all are true:

1. it is clearly marked as a test
2. it is sent to the selected operator target only
3. it does not trigger real external requests
4. it does not create domain commands
5. it does not change runtime posture outside the alerting tool path itself

## Ack evidence constraints

The first real ack evidence bundle must include at least:

- rule id / alert id
- severity
- triggered at UTC
- delivered target
- operator
- ack response
- ack time UTC
- screenshot or copied Telegram message
- copied operator response
- linked GitHub issue / ops log reference when applicable

## Not authorized by this review

This document does **not** authorize:

- storing Telegram secrets in the repository
- silently wiring a live tool without a written closeout
- broad alert automation beyond the selected bounded path
- changing backend code
- changing `.env` without an explicit wiring task
- real external request
- live trading

## Recommended next task

- **`Alert Platform Wiring Decision + First Test Alert Plan`**

That task should decide:

- exact Telegram delivery mechanism
- exact secret-handling method
- exact test-alert path
- exact ack-evidence storage path

After that, a separate execution task should perform the first bounded test
alert and collect the ack evidence bundle.

## Effect on checklist state

Current effect:

- **`Alert rules + routing implemented`**: remain **`IN_PROGRESS`**
- **`G2 — P0/P1 alerting verified (test alert acked)`**: remain **`NOT DONE`**

This review authorizes the next operational step, but does not itself satisfy
either Week 3 closeout gate.

## Final authorization result

- Telegram wiring authorized: YES
- Secret-handling decision required: YES
- Test-alert decision required: YES
- Ack-evidence collection required: YES
- Live Telegram wiring performed by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Recommended next task: **`Alert Platform Wiring Decision + First Test Alert Plan`**
- Real external request authorized: NO
- Live trading: NO-GO

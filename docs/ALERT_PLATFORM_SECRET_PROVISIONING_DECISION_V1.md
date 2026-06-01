# Alert Platform Secret Provisioning Decision V1

## Status

- Decision type: secret provisioning decision only
- Telegram secret configured by this document: NO
- Telegram secret values recorded by this document: NO
- Telegram wiring performed by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Purpose

This document fixes the minimal provisioning model required before the first
Telegram wiring execution can proceed.

It answers:

- who prepares the Telegram secret material
- where the secret material should live
- how presence is verified without revealing values
- what must stay out of git and out of evidence artifacts

This document does **not** configure any secret and does **not** send any
alert.

## Current blocker

The first alert-platform wiring precheck on the stage host stopped correctly.

Observed blocker:

- `TELEGRAM_NOTIFY_ENABLED_VALUE_OK=NO`
- `TELEGRAM_BOT_TOKEN_PRESENT=NO`
- `TELEGRAM_CHAT_ID_PRESENT=NO`
- `/ops/worker.telegram_enabled=false`

So the remaining problem is not design quality. It is secret readiness.

## Decision

### Decision result

- Telegram secret provisioning path defined: YES
- Telegram secret configured by this decision: NO
- Presence-only validation path defined: YES
- Week 3 alerting row moved to DONE by this decision: NO

## Provisioning owner

Provisioning owner:

- **`baolood`** as operator / security owner in solo internal review mode

This means one named operator is responsible for:

- preparing the Telegram bot token
- preparing the Telegram chat id
- placing them into the approved host-local location
- confirming that the values are injected into runtime without exposing them in
  git or evidence

## Provisioning location decision

The chosen provisioning model is:

- **host-local operator-managed env file outside the repository**

Preferred path:

- **`/etc/project-anchor/alerting.env`**

Required properties:

1. outside the git checkout
2. readable only by the operator / root-owned runtime path
3. not copied into docs, artifacts, issues, or PR text
4. suitable for runtime injection into the backend container

### Required variable names

The provisioning path must supply exactly these variables:

```text
TELEGRAM_NOTIFY_ENABLED
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Expected non-secret posture:

- `TELEGRAM_NOTIFY_ENABLED=1`
- `TELEGRAM_BOT_TOKEN` present and non-empty
- `TELEGRAM_CHAT_ID` present and non-empty

## What must not happen

The provisioning step must **not**:

- store token or chat id in the repository
- write token or chat id into tracked docs
- paste token or chat id into terminal transcripts kept in git
- place token or chat id into `artifacts/alerting/`
- modify `.env` inside the repository
- commit any secret-bearing override file

## Presence-only validation decision

The accepted validation model is:

- verify existence and non-emptiness only
- never print the token value
- never print the chat id value in full

Accepted validation questions:

1. is `TELEGRAM_NOTIFY_ENABLED` exactly `1`?
2. is `TELEGRAM_BOT_TOKEN` present and non-empty?
3. is `TELEGRAM_CHAT_ID` present and non-empty?
4. does `/ops/worker` report `telegram_enabled=true`?

Accepted validation output shape:

```text
TELEGRAM_NOTIFY_ENABLED_VALUE_OK=YES|NO
TELEGRAM_BOT_TOKEN_PRESENT=YES|NO
TELEGRAM_CHAT_ID_PRESENT=YES|NO
telegram_enabled=true|false
```

## Runtime injection expectation

The next execution step may assume:

- backend runtime reads Telegram env values from host-local provisioning
- no repo-tracked file is used as the source of truth
- container-level presence checks are allowed
- presence checks must remain value-free

This decision intentionally stays silent on the exact compose / runtime wiring
command. That belongs to the bounded execution step.

## Evidence rule

Evidence may record only:

- secret source class
- provisioning owner
- presence check result
- non-secret enabled/disabled state

Evidence must **not** record:

- token value
- full chat id value
- copied env file content
- screenshots containing secrets

## Failure stop rules

The first wiring execution must stop immediately if any of the following are
true:

1. `/etc/project-anchor/alerting.env` does not exist
2. file exists but secret presence cannot be checked without printing values
3. runtime cannot see the variables after bounded injection
4. `telegram_enabled` remains false after the intended non-secret enablement
   step
5. any secret value appears in terminal output or evidence draft

If a stop rule triggers:

- do not send the test alert
- do not keep partial secret material in repo files
- record the failure as provisioning not ready

## Recommended next task

- **`Alert Platform Secret Provisioning Operator Step`**

That operator step should:

1. create the host-local env file if absent
2. place `TELEGRAM_NOTIFY_ENABLED=1`
3. place non-empty `TELEGRAM_BOT_TOKEN`
4. place non-empty `TELEGRAM_CHAT_ID`
5. keep permissions restricted
6. return only presence-proof output, not values

After that, rerun:

- **`Alert Platform First Wiring Execution Precheck`**

## Effect on checklist state

Current effect:

- **`Alert rules + routing implemented`**: remain **`IN_PROGRESS`**
- **`G2 — P0/P1 alerting verified (test alert acked)`**: remain **`NOT DONE`**

This decision removes provisioning ambiguity but does not itself create the
required alert-path evidence.

## Final decision

- Provisioning owner: **`baolood`**
- Provisioning path: **`/etc/project-anchor/alerting.env`**
- Variable names fixed: YES
- Presence-only validation path fixed: YES
- Secret values recorded in repo: NO
- Wiring performed by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

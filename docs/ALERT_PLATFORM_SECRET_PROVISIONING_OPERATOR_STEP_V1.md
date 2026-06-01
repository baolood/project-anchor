# Alert Platform Secret Provisioning Operator Step V1

## Status

- Document type: operator step only
- Secret values recorded by this document: NO
- Secret values configured by this document: NO
- Telegram wiring performed by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Purpose

This document defines the bounded operator step required to make Telegram secret
material available on the stage host without disclosing values in git or in
evidence artifacts.

It does **not** contain secret values.

It narrows the operator action to:

1. placing the required variables into the approved host-local location
2. setting safe file permissions
3. confirming secret presence without printing values

## Preconditions

The following must already be true:

- **`docs/ALERT_PLATFORM_SECRET_PROVISIONING_DECISION_V1.md`** exists
- provisioning owner remains **`baolood`**
- approved provisioning path remains **`/etc/project-anchor/alerting.env`**
- variable names remain:
  - **`TELEGRAM_NOTIFY_ENABLED`**
  - **`TELEGRAM_BOT_TOKEN`**
  - **`TELEGRAM_CHAT_ID`**

## Target host

Current target host:

- hostname: `vultr`
- repo path: `/root/project-anchor`
- alerting env target: `/etc/project-anchor/alerting.env`

## Required file shape

The host-local file must contain:

```text
TELEGRAM_NOTIFY_ENABLED=1
TELEGRAM_BOT_TOKEN=<non-empty secret value>
TELEGRAM_CHAT_ID=<non-empty target value>
```

Rules:

- values must not be copied into git
- values must not be copied into evidence artifacts
- comments are optional, but should not include secret material

## File ownership and permissions

Minimum file safety rule:

- owner: root or operator-controlled privileged account
- permissions: readable only by the intended runtime / operator path

Recommended posture:

```text
owner: root
mode: 600
path: /etc/project-anchor/alerting.env
```

## Bounded operator procedure

The operator step should do only the following:

1. ensure `/etc/project-anchor/` exists
2. create or replace `/etc/project-anchor/alerting.env`
3. place the three required variables into that file
4. set restrictive file permissions
5. confirm presence without printing the values

The operator step should **not**:

- paste the values into repo files
- keep the values in shell history if avoidable
- print the token value
- print the full chat id value
- send a Telegram message yet

## Presence-only validation commands

Accepted validation outputs must remain value-free.

The operator may use an equivalent value-safe check, but the outcome must map
to this shape:

```text
TELEGRAM_NOTIFY_ENABLED_VALUE_OK=YES|NO
TELEGRAM_BOT_TOKEN_PRESENT=YES|NO
TELEGRAM_CHAT_ID_PRESENT=YES|NO
```

The operator may also confirm:

```text
ALERTING_ENV_FILE_PRESENT=YES|NO
ALERTING_ENV_FILE_PERMS_OK=YES|NO
```

## Evidence rule

The operator step may record only:

- host identity
- path identity
- file presence
- permission result
- presence-only YES/NO results

The operator step must **not** record:

- token value
- full chat id value
- literal env file content
- screenshots containing raw secret material

## Failure stop rules

Stop immediately if any of the following are true:

1. `/etc/project-anchor/alerting.env` cannot be created safely
2. values can only be validated by printing them
3. file permissions cannot be restricted
4. the operator is unsure whether the target chat is the intended one
5. evidence output would expose secret material

If a stop rule triggers:

- do not continue to wiring execution
- record provisioning as `NOT READY`
- do not send any test alert

## Output expected from this step

Expected safe summary shape:

```text
[Alert Platform Secret Provisioning Operator Step]
host:
path:
alerting env file present: YES/NO
alerting env file perms ok: YES/NO
TELEGRAM_NOTIFY_ENABLED_VALUE_OK: YES/NO
TELEGRAM_BOT_TOKEN_PRESENT: YES/NO
TELEGRAM_CHAT_ID_PRESENT: YES/NO
secret values disclosed: NO
next decision:
- rerun Alert Platform First Wiring Execution Precheck: YES/NO
```

## What this step does not do

This step does **not**:

- modify tracked repository files
- perform Telegram wiring
- send the first test alert
- collect ack evidence
- authorize real external request
- authorize live trading

## Recommended next task

- **`Alert Platform First Wiring Execution Precheck`**

Only after this operator step returns safe YES/NO presence proof should the
project retry the first wiring execution precheck.

## Final operator-step result

- Provisioning path explicit: YES
- Variable names explicit: YES
- Presence-only validation explicit: YES
- Secret value disclosure allowed: NO
- Telegram wiring performed by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

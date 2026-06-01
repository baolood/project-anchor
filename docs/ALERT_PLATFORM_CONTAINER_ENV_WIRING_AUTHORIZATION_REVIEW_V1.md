# Alert Platform Container Env Wiring Authorization Review V1

## Status

- Review type: container env wiring authorization only
- Host-local Telegram secret file provisioned before this review: YES
- Container env wiring for Telegram present before this review: NO
- Container env wiring authorized by this review: YES
- Compose recreate authorized by this review: YES, bounded
- Wiring performed by this document: NO
- Test alert fired by this document: NO
- Ack evidence collected by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Question under review

The current stage host appears to have:

- `/etc/project-anchor/alerting.env` present on host
- presence-only secret checks passing on host

But the running containers still show:

- `TELEGRAM_NOTIFY_ENABLED` absent
- `TELEGRAM_BOT_TOKEN` absent
- `TELEGRAM_CHAT_ID` absent
- `/ops/worker.telegram_enabled=false`

So the remaining question is:

- should the project now authorize wiring `/etc/project-anchor/alerting.env`
  into the backend / worker containers and one bounded compose recreate to load
  those variables?

This review does **not** perform the wiring.

## Current evidence

### Host-side secret provisioning

Per the project’s current operator outcome:

- host-local secret provisioning: complete
- provisioning path: **`/etc/project-anchor/alerting.env`**
- presence-only validation: complete

### Code-side env usage

The code already reads:

- **`TELEGRAM_NOTIFY_ENABLED`**
- **`TELEGRAM_BOT_TOKEN`**
- **`TELEGRAM_CHAT_ID`**

Specifically:

- **`anchor-backend/app/ops/notify.py`**
- **`anchor-backend/app/main.py`**

And `/ops/worker` already exposes non-secret:

- `telegram_enabled`

### Compose-side gap

Current compose files show:

- `anchor-backend/docker-compose.yml`: no Telegram env wiring
- `anchor-backend/docker-compose.override.yml`: no Telegram env wiring
- no visible `env_file` reference to **`/etc/project-anchor/alerting.env`**

So the blocker is now clearly:

- host secret exists
- runtime container env does not receive it

## Decision

### Decision result

- Container env wiring authorization: YES
- Bounded compose recreate authorization: YES
- Test alert authorized by this review: NO
- Week 3 alerting row moved to DONE by this review: NO

### Why this is now appropriate

We are no longer deciding whether Telegram is the right platform, whether
secrets should exist, or whether the first alert plan is safe.

Those questions are already closed.

The remaining blocker is operational and narrow:

- inject the already-approved host-local file into the intended containers
- recreate only the affected containers
- verify presence without disclosing values

That is exactly the kind of bounded infrastructure change that should now be
authorized.

## Scope of the next authorized task

The next task may do only the following:

1. add an `env_file` or equivalent compose env wiring path for:
   - backend
   - worker
2. point that wiring to:
   - **`/etc/project-anchor/alerting.env`**
3. perform one bounded compose recreate of only the affected services
4. verify container-side env presence without printing values
5. verify `/ops/worker.telegram_enabled=true` after successful reload

## Bounded mutate surface

The next task may mutate only:

- compose env wiring for backend / worker
- backend / worker container runtime state via bounded recreate

It must **not**:

- edit repo-tracked `.env`
- expose secret values in logs or artifacts
- restart unrelated services without cause
- send the test alert yet
- touch domain command flows
- change risk / kill switch / execution posture

## Required validation after wiring

The next task must produce only non-secret output proving:

```text
BACKEND_ENV_TELEGRAM_NOTIFY_ENABLED_PRESENT=YES|NO
BACKEND_ENV_TELEGRAM_BOT_TOKEN_PRESENT=YES|NO
BACKEND_ENV_TELEGRAM_CHAT_ID_PRESENT=YES|NO
WORKER_ENV_TELEGRAM_NOTIFY_ENABLED_PRESENT=YES|NO
WORKER_ENV_TELEGRAM_BOT_TOKEN_PRESENT=YES|NO
WORKER_ENV_TELEGRAM_CHAT_ID_PRESENT=YES|NO
OPS_WORKER_TELEGRAM_ENABLED=true|false
```

No token value and no full chat id may be printed.

## Recreate boundary

The first authorized recreate should be:

- backend + worker only

It should not automatically:

- rebuild unrelated images
- bounce postgres
- bounce redis
- run a deploy wider than the alerting env change requires

## Failure stop rules

The next task must stop immediately if any of the following occur:

1. wiring would require placing secret values into repo-tracked files
2. container-side verification can only be done by printing values
3. backend / worker fail to return healthy after recreate
4. `/ops/worker.telegram_enabled` remains false after the bounded reload
5. any step appears to drift into test-alert send before verification is done

If a stop rule triggers:

- stop at wiring failure
- do not send test alert
- record the failure
- keep Week 3 alerting `IN_PROGRESS`

## Not authorized by this review

This review does **not** authorize:

- test alert send
- ack evidence collection
- auto-escalation verification
- multi-target Telegram routing
- generalized compose refactor
- real external request
- live trading

## Recommended next task

- **`Alert Platform Container Env Wiring Execution`**

That task should:

1. add the bounded env wiring
2. recreate backend / worker only
3. run presence-only container verification
4. verify `/ops/worker.telegram_enabled=true`
5. stop before test alert send

## Effect on checklist state

Current effect:

- **`Alert rules + routing implemented`**: remain **`IN_PROGRESS`**
- **`G2 — P0/P1 alerting verified (test alert acked)`**: remain **`NOT DONE`**

This review only authorizes the wiring step. It does not create the alert-path
ack evidence required for closure.

## Final authorization result

- Host-local secret provisioned: YES
- Container env wiring present before review: NO
- Container env wiring now authorized: YES
- Bounded backend / worker recreate authorized: YES
- Test alert authorized by this review: NO
- Wiring performed by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

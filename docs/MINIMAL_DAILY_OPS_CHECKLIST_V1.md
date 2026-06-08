# Minimal Daily Ops Checklist V1

**Status:** daily-check checklist only. No deploy, no runtime mutation, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-06-08**

## 1. Purpose

This checklist is the shortest acceptable daily operations check for the current Project Anchor posture.

It exists to answer one narrow question:

```text
is the current review/runtime path obviously healthy enough
to leave the system in normal monitored posture for today?
```

This checklist is intentionally smaller than the longer lead-review guides.
It is meant for a **2–5 minute** daily check, not for deep investigation.

## 2. Current Scope

Use this checklist only for the current bounded posture:

- mainline merged and stable
- cloud host aligned
- canonical `TESTNET_*` runtime aligned
- bounded controlled testnet execution already proven
- `go-live`: `NO-GO`
- `live trading`: `NO-GO`

This checklist does **not** authorize:

- deploys
- runtime edits
- DNS / ingress changes
- real production execution

## 3. Daily Check Modes

There are two acceptable daily-check modes:

### A. Browser / SSH-tunnel mode

Use:

- `/health`
- `/ops/state`
- `/ops/worker`

This is the preferred fastest path.

### B. Terminal readonly mode

Use readonly curl / status checks only when browser access is inconvenient.

Do not turn terminal quick checks into ad hoc debugging unless the checklist fails.

## 4. Minimum Daily Check Order

Always check in this order:

```text
/health -> /ops/state -> /ops/worker
```

Why this order:

1. first confirm backend liveness
2. then confirm system posture
3. then confirm worker + alert path

## 5. PASS Signals

### 5.1 `/health`

Expected:

```json
{"ok": true}
```

If `/health` is not readable or does not return `ok=true`, result is immediately:

```text
BLOCKED
```

### 5.2 `/ops/state`

Check these minimum fields:

- `kill_switch.enabled=false`
- `worker_heartbeat.last_heartbeat_at` present
- `worker_heartbeat.last_seen_at` present
- `recent_ops_events` not showing a new unexplained operator anomaly

Minimum interpretation:

```text
system posture readable
kill switch not engaged
worker heartbeat fresh enough to be believable
```

### 5.3 `/ops/worker`

Check these minimum fields:

- `kill_switch_enabled=false`
- `kill_switch_source=none`
- `telegram_enabled=true`
- `last_heartbeat_at` present and fresh

Minimum interpretation:

```text
worker alive
alert path enabled
no active kill boundary
```

## 6. Minimal PASS Rule

Daily check is `PASS` only if all are true:

1. `/health` returns `ok=true`
2. `/ops/state` is readable
3. `/ops/worker` is readable
4. kill switch is off in both places
5. worker heartbeat is fresh/readable
6. Telegram alert path is enabled

If all six are true, the daily conclusion may be:

```text
PASS - runtime posture looks healthy enough for normal bounded monitoring
```

## 7. Minimal BLOCKED Rule

Use `BLOCKED` if any of the following is true:

- `/health` unreadable
- `/ops/state` unreadable
- `/ops/worker` unreadable
- kill switch unexpectedly enabled
- worker heartbeat missing/stale
- Telegram alert path unexpectedly disabled
- page results contradict each other

`BLOCKED` means:

```text
do not improvise
switch from daily check to targeted technical review
```

## 8. What Not To Do During Daily Check

Do **not** turn the daily check into any of the following unless a separate task requires it:

- deploy
- restart services
- edit env files
- edit DNS / ingress
- trigger real testnet execution
- trigger production execution
- open live-trading discussion
- grep random logs until a preferred story appears

The daily checklist is for posture confirmation, not for opportunistic changes.

## 9. Minimal Recording Template

Use this exact short form:

```text
[MINIMAL_DAILY_OPS_CHECK]
time:
mode: browser / readonly-terminal
health_ok: yes/no
ops_state_readable: yes/no
ops_worker_readable: yes/no
kill_switch_off: yes/no
worker_heartbeat_fresh: yes/no
telegram_enabled: yes/no
verdict: PASS / BLOCKED
notes:
```

## 10. Good Default Daily Verdict

If the current known healthy posture is still visible, the expected normal daily result is:

```text
PASS
kill switch off
worker heartbeat fresh
telegram enabled
no further action needed
```

## 11. Escalation Rule

Escalate from daily-check mode to deeper review only if:

- one of the minimum fields fails
- browser/readonly checks contradict prior expected posture
- the host appears drifted from mainline/runtime alignment expectations

If escalation is needed, move to:

- `LEAD_DAILY_CHECK_GUIDE_V1`
- cloud-host readonly status pack
- cloud-host alignment review

Do not mix those deeper steps into the daily checklist by default.

## 12. One-Line Rule

```text
Every normal day, just verify health, system posture, worker heartbeat, and Telegram alerting; if those are clean, stop there.
```

# Dry-run smoke runbook V1

**Status:** active smoke runbook for the Trade Gate dry-run path.

**Owner:** **baolood** (Engineering / Operations lead, interim).

**Scope:** this runbook validates the pre-live dry-run chain only:

```text
/trade-gate
-> Next same-origin proxy
-> SSH tunnel
-> cloud backend
-> commands_domain
-> domain_command_worker
-> risk
-> DONE / FAILED
```

It does **not** enable live trading. Do not add API keys, connect an exchange, place real orders, relax risk limits, or change backend / worker / risk code while running this smoke.

## Preconditions

| Check | Expected |
|-------|----------|
| Parent repo | `git status --short` is clean before the smoke |
| Console repo | `anchor-console` `git status --short` is clean |
| Cloud backend | latest dry-run endpoint deployed |
| Cloud worker | latest worker image running |
| SSH access | `root@45.76.190.109` reachable |
| Live trading | **NO-GO** |

## Terminal A: open the backend tunnel

Keep this terminal open for the full smoke.

```bash
ssh -N -L 18000:127.0.0.1:8000 root@45.76.190.109
```

In another terminal, confirm the tunnel reaches the cloud backend:

```bash
curl -i --max-time 10 http://127.0.0.1:18000/health
```

Expected:

```text
HTTP/1.1 200 OK
{"ok":true}
```

## Terminal B: start the console against the tunnel

```bash
cd /path/to/project-anchor/anchor-console
BACKEND_URL=http://127.0.0.1:18000 npm run dev
```

Expected:

```text
http://localhost:3000
```

Do not use `NEXT_PUBLIC_API_BASE` for this smoke. The browser should call the same-origin Next proxy, and the Next server should forward through `BACKEND_URL`.

## Terminal C: run the smoke script

Run from the parent repo:

```bash
cd /path/to/project-anchor
BACKEND_PRECHECK=http://127.0.0.1:18000 \
CONSOLE_URL=http://127.0.0.1:3000 \
./scripts/checklist_trade_gate_dry_run_e2e.sh
```

The script submits two dry-run intents:

| Path | Default notional | Expected result |
|------|------------------|-----------------|
| Risk-failed path | `FAILED_NOTIONAL=10` | `FAILED` with `RISK_HARD_LIMITS` |
| DONE path | `DONE_NOTIONAL=4` | `DONE` with worker events |

If the risk state changes and the DONE path is blocked, lower the test notional for the smoke run. Do **not** weaken risk rules to force a pass.

Example override:

```bash
BACKEND_PRECHECK=http://127.0.0.1:18000 \
CONSOLE_URL=http://127.0.0.1:3000 \
FAILED_NOTIONAL=10 \
DONE_NOTIONAL=2 \
./scripts/checklist_trade_gate_dry_run_e2e.sh
```

## PASS criteria

The final output must include:

```text
FAILED_STATUS=FAILED
FAILED_ERROR=RISK_HARD_LIMITS...
DONE_STATUS=DONE
DONE_EVENTS_HAS_PICKED=YES
DONE_EVENTS_HAS_POLICY_ALLOW=YES
DONE_EVENTS_HAS_ACTION_OK=YES
DONE_EVENTS_HAS_MARK_DONE=YES
PASS_OR_FAIL=PASS
FAIL_REASON=
```

## What each result means

- `FAILED` with `RISK_HARD_LIMITS` means the risk hard-limit guardrail blocked an unsafe dry-run request. This is a valid smoke result.
- `DONE` means a small dry-run order intent was accepted by risk, consumed by the worker, and marked complete.
- `UNKNOWN_TYPE` means the command entered the chain with a type the worker does not recognize, or the cloud worker is stale. Rebuild / redeploy the worker before changing code.
- `PASS_OR_FAIL=FAIL` means the run is not accepted until the `FAIL_REASON` is understood.

## Troubleshooting

| Symptom | Likely cause | Next check |
|---------|--------------|------------|
| `BACKEND_PRECHECK_HTTP_000` or timeout | SSH tunnel closed, wrong port, or backend not listening | Reopen tunnel and retry `/health` |
| `CONSOLE_TRADE_GATE_NOT_READY_HTTP_000` | Next dev server not running | Restart `npm run dev` with `BACKEND_URL=http://127.0.0.1:18000` |
| Submit returns `404` | Next proxy route missing or wrong console build | Check `/api/trade-gate/dry-run-intents` exists in `anchor-console` |
| Command detail returns `404` | Wrong `command_id`, stale detail proxy, or backend did not persist command | Check `/commands` and `/commands/[id]` |
| Proxy returns `500` | Backend returned an error or proxy could not reach upstream | Check Next terminal and backend logs |
| `UNKNOWN_TYPE` | Worker/backend command type mismatch or stale worker | Rebuild / restart cloud worker; do not remap order to quote |
| DONE events missing | Worker did not emit expected lifecycle events | Check command events endpoint and worker logs |

## Stop the smoke environment

1. Stop the Next dev server with `Ctrl+C`.
2. Stop the SSH tunnel with `Ctrl+C`.
3. Confirm both repos are clean:

```bash
cd /path/to/project-anchor/anchor-console
git status --short

cd /path/to/project-anchor
git status --short
```

## Acceptance record

Record each accepted run with:

```text
[Dry Run E2E Smoke]
date:
parent commit:
anchor-console commit:
FAILED_ID:
FAILED_STATUS:
FAILED_ERROR:
DONE_ID:
DONE_STATUS:
DONE_EVENTS_HAS_PICKED:
DONE_EVENTS_HAS_POLICY_ALLOW:
DONE_EVENTS_HAS_ACTION_OK:
DONE_EVENTS_HAS_MARK_DONE:
PASS_OR_FAIL:
live trading: NO-GO
```

This runbook supports pre-live validation only. CI green and smoke PASS do not approve live trading.

# Synthetic Checks Execution Authorization Review V1

## Status

- Review type: authorization review only
- First controlled synthetic check execution authorized: YES
- Synthetic checks executed by this document: NO
- Scheduled automation authorized: NO
- External alerting platform integration authorized: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Background

The Week 3 synthetic checks baseline is now explicit in
**`docs/SYNTHETIC_CHECKS_CRITICAL_ENDPOINTS_V1.md`**.

Current supporting documents:

- **`docs/SERVICE_SLI_SLO.md`**
- **`docs/ALERTING_ROUTING.md`**
- **`docs/SYNTHETIC_CHECKS_CRITICAL_ENDPOINTS_V1.md`**

The current baseline defines the minimum critical endpoint set:

| Check ID | Surface | Probe |
|---|---|---|
| **`SC-HEALTH`** | **`GET /health`** | `curl -sS http://127.0.0.1:8000/health` |
| **`SC-OPS`** | **`GET /ops/state`** | `curl -sS http://127.0.0.1:8000/ops/state` |
| **`SC-WORKER`** | worker heartbeat freshness via **`/ops/state`** | inspect heartbeat freshness in **`/ops/state`** response |
| **`SC-PARENT`** | parent guardrail checks | `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh` and `bash scripts/check_go_live_rules.sh` |

This review answers whether the project may run the first controlled synthetic
check execution on the stage host.

## Authorization question

Should the project authorize the first controlled execution of the synthetic
checks defined in **`docs/SYNTHETIC_CHECKS_CRITICAL_ENDPOINTS_V1.md`**?

## Decision

Authorization decision: YES.

The project may proceed to one controlled synthetic check execution task using
the boundary and stop conditions below.

This authorization does **not** authorize:

- scheduled automation
- alert-platform integration
- real external request
- live trading
- credential changes
- kill switch changes
- runtime mode changes
- unrelated deploy changes

## Authorized execution scope

The next synthetic check execution task may authorize:

- SSH to the target stage host
- read-only host / repo / runtime precheck
- one manual execution of the synthetic check probes
- one manual parent guardrail check block
- result classification
- evidence closeout

Target stage host:

- Provider / role: Vultr Project Anchor stage host
- Public IP: **`45.76.190.109`**
- Hostname: **`vultr`**
- Repo path: **`/root/project-anchor`**
- Backend base URL: **`http://127.0.0.1:8000`**

## Required precheck

Before running probes, collect:

```bash
hostname
date -Is
cd /root/project-anchor
pwd
git rev-parse --short HEAD
git status -sb
python3 --version || true
python3.11 --version || true
which python3 || true
which python3.11 || true
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

The task must stop before probe execution if the host identity, repo path, or
Docker runtime state is unclear.

## Authorized synthetic check probes

Run these probes manually in the next controlled execution task:

```bash
cd /root/project-anchor
echo "=== SYNTHETIC CHECK EXECUTION @ $(date -u -Is) ==="
echo "=== SC-HEALTH ==="
curl -sS http://127.0.0.1:8000/health
echo
echo "=== SC-OPS ==="
curl -sS http://127.0.0.1:8000/ops/state
echo
echo "=== SC-PARENT ==="
PYTHON=python3.11 bash scripts/check_local_box_baseline.sh
bash scripts/check_go_live_rules.sh
echo "=== FINAL GIT STATUS ==="
git status -sb
```

**`SC-WORKER`** must be classified from the **`/ops/state`** response:

- worker heartbeat visible: YES/NO
- worker heartbeat freshness <= 60s: YES/NO
- worker panic visible: YES/NO

## Pass / fail rules

The first controlled synthetic check execution may be marked PASS only if all
are true:

- `SC-HEALTH`: `/health` returns success
- `SC-OPS`: `/ops/state` is reachable
- `SC-WORKER`: worker heartbeat is visible and fresh within the SLO-4 threshold
- `SC-PARENT`: `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh` passes
- `SC-PARENT`: `bash scripts/check_go_live_rules.sh` passes
- git dirty state is recorded
- no new command is created
- no credential change occurs
- no kill switch change occurs
- no deploy occurs
- no backend or worker restart occurs
- real external request remains NOT AUTHORIZED
- live trading remains NO-GO

## Not authorized

This authorization does **not** allow:

- cron / scheduler setup
- external alerting platform setup
- Slack / Telegram / PagerDuty / email integration
- alert acknowledgement simulation
- backend code changes
- deploy
- Docker restart
- worker restart
- credential changes
- `.env` changes
- kill switch changes
- new command creation
- real external request
- live trading

## Evidence template for next task

```text
[Synthetic Checks First Controlled Execution Evidence]
host:
- hostname:
- repo path:
- git revision:
- git status:
runtime:
- docker status visible: YES/NO
checks:
- SC-HEALTH: PASS/FAIL
- SC-OPS: PASS/FAIL
- SC-WORKER heartbeat visible: YES/NO
- SC-WORKER heartbeat fresh <= 60s: YES/NO
- SC-PARENT baseline: PASS/FAIL
- SC-PARENT go-live rules: PASS/FAIL
boundary:
- new command created: NO
- deploy performed: NO
- backend restarted: NO
- worker restarted: NO
- credential changed: NO
- kill switch changed: NO
- real external request: NOT AUTHORIZED
- live trading: NO-GO
decision:
- first controlled synthetic check execution: PASS/FAIL
- Week 3 synthetic checks row ready for DONE: YES/NO
```

## Failure handling

If any probe fails:

1. Stop.
2. Do not restart services.
3. Do not repair runtime.
4. Record the failing check.
5. Record visible runtime state.
6. Keep real external request NOT AUTHORIZED.
7. Keep live trading NO-GO.

Failure closeout must state:

```text
[Synthetic Checks First Controlled Execution Failure]
failed check:
observed result:
runtime state:
operator decision:
- continue: NO
- recovery action authorized: YES/NO
real external request: NOT AUTHORIZED
live trading: NO-GO
```

## Final authorization result

- First controlled synthetic check execution authorization: YES
- Synthetic checks executed by this document: NO
- Scheduled automation authorized: NO
- External alerting platform integration authorized: NO
- Recommended next task: Synthetic Checks First Controlled Execution
- Real external request authorized: NO
- Live trading: NO-GO

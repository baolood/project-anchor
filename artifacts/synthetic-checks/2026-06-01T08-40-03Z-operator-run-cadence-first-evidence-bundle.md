# Synthetic Checks Operator-Run Cadence Evidence Bundle

## Metadata

- Execution type: operator-run cadence evidence bundle
- Execution timestamp (UTC): `2026-06-01T08:40:03Z`
- Operator: `baolood`
- Qualification: `solo internal review mode`
- Hostname: `vultr`
- Repo path: `/root/project-anchor`
- Git revision: `d76bb0a`
- Git status at start:
  - `## HEAD (no branch)`
  - `M anchor-backend/docker-compose.override.yml`

## Runtime precheck

- Python 3: `Python 3.10.12`
- Python 3.11: `Python 3.11.0rc1`
- `which python3`: `/usr/bin/python3`
- `which python3.11`: `/usr/bin/python3.11`

Docker visibility:

- `anchor-backend-backend-1`: `Up 6 hours`
- `anchor-backend-worker-1`: `Up 6 hours`
- `anchor-backend-postgres-1`: `Up 3 weeks`
- `anchor-backend-redis-1`: `Up 3 weeks`

## Probe results

### `SC-HEALTH`

- Command:
  - `curl -sS http://127.0.0.1:8000/health`
- Result:
  - `{"ok":true}`
- Classification:
  - PASS

### `SC-OPS`

- Command:
  - `curl -sS http://127.0.0.1:8000/ops/state`
- Result:
  - reachable
  - `kill_switch.enabled = false`
  - worker heartbeat visible
  - `worker_panic = null`
- Classification:
  - PASS

### `SC-WORKER`

Derived from `SC-OPS` response:

- `worker_heartbeat.last_heartbeat_at`:
  - `2026-06-01T08:39:53.141751Z`
- `/ops/state generated_at`:
  - `2026-06-01T08:40:08.060562Z`
- freshness:
  - approximately `15s`
- threshold:
  - `<= 60s`
- panic visible:
  - `NO`

Classification:

- PASS

### `SC-PARENT`

Commands:

- `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh`
- `bash scripts/check_go_live_rules.sh`

Results:

- parent baseline:
  - PASS
- go-live rules:
  - PASS

Classification:

- PASS

## Boundary confirmation

- New command created: NO
- Deploy performed: NO
- Backend restarted: NO
- Worker restarted: NO
- Credential changed: NO
- Kill switch changed: NO
- Real external request: NOT AUTHORIZED
- Live trading: NO-GO

## Final git status

- `## HEAD (no branch)`
- `M anchor-backend/docker-compose.override.yml`

## Final decision

- Operator-run cadence evidence bundle: PASS
- Synthetic checks active under accepted current path: YES
- Week 3 synthetic checks row ready for DONE from activation-path perspective: YES
- Real external request authorized: NO
- Live trading: NO-GO

# Synthetic checks for critical endpoints (Week 3 baseline V1)

**Status:** baseline V1 — critical endpoint synthetic check scope, probe method, pass/fail rules, and evidence expectations are now explicit. This does **not** mean the checks are already automated, scheduled, or integrated with an external alerting platform.

**Pairs with:** **`docs/SERVICE_SLI_SLO.md`** (SLOs define what matters), **`docs/ALERTING_ROUTING.md`** (thresholds and routing expectations), **`docs/STAGE_DEPLOY_RUNBOOK.md`** (existing bounded probe commands), and **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 3.

**Owner:** **baolood** (Engineering lead / operations lead, interim).

## 1) Purpose

This document defines the minimum synthetic-check baseline for the current single-host stage posture.

The intent is to answer, with no new tooling yet:

- which endpoints count as critical;
- how they should be probed;
- what counts as PASS vs FAIL;
- which SLI / alert rule each probe supports; and
- what evidence must exist before the Week 3 checklist row can honestly move to **`DONE`**.

## 2) Current observable surfaces

The current baseline is intentionally limited to surfaces that already exist and have already been exercised during bounded deploy / rollback validation:

- **`GET /health`**
- **`GET /ops/state`**
- worker heartbeat visibility through **`/ops/state`**
- bounded parent checks:
  - **`PYTHON=python3.11 bash scripts/check_local_box_baseline.sh`**
  - **`bash scripts/check_go_live_rules.sh`**

These are the same surfaces already referenced by:

- **`docs/STAGE_DEPLOY_RUNBOOK.md`**
- **`docs/ONE_COMMAND_DEPLOYMENT_RUNBOOK_FIRST_CONTROLLED_VALIDATION_CLOSEOUT_V1.md`**
- **`docs/ROLLBACK_DRILL_FIRST_DESTRUCTIVE_EXECUTION_CLOSEOUT_V1.md`**

## 3) Critical endpoint set (V1)

| Check ID | Surface | Why critical | Current probe method |
|---|---|---|---|
| **`SC-HEALTH`** | **`GET /health`** | Primary API reachability / availability signal | `curl -sS http://127.0.0.1:8000/health` |
| **`SC-OPS`** | **`GET /ops/state`** | Operational state visibility, kill switch visibility, worker-state visibility | `curl -sS http://127.0.0.1:8000/ops/state` |
| **`SC-WORKER`** | worker heartbeat freshness via **`/ops/state`** | Worker liveness and freshness signal | inspect heartbeat freshness in **`/ops/state`** response |
| **`SC-PARENT`** | parent guardrail checks | Confirms parent orchestration / guardrail posture still passes after bounded stage actions | `PYTHON=python3.11 bash scripts/check_local_box_baseline.sh` and `bash scripts/check_go_live_rules.sh` |

## 4) V1 probe expectations

### `SC-HEALTH`

- Probe:
  ```bash
  curl -sS http://127.0.0.1:8000/health
  ```
- PASS when:
  - request succeeds; and
  - response indicates healthy API state (current bounded evidence uses **`{"ok":true}`**).
- FAIL when:
  - request fails; or
  - response is missing / malformed; or
  - response does not indicate healthy state.

### `SC-OPS`

- Probe:
  ```bash
  curl -sS http://127.0.0.1:8000/ops/state
  ```
- PASS when:
  - request succeeds; and
  - operational state is visible enough to inspect kill switch state and worker heartbeat.
- FAIL when:
  - request fails; or
  - response is absent / malformed; or
  - worker / kill-switch visibility is unavailable.

### `SC-WORKER`

- Probe source:
  - worker heartbeat field in **`/ops/state`**
- PASS when:
  - worker heartbeat is visible; and
  - freshness is within the agreed Week 3 SLO support threshold (**`<= 60s`**).
- FAIL when:
  - worker heartbeat is stale over **`60s`** at observation time; or
  - worker heartbeat is absent; or
  - worker appears crashed / stuck.

### `SC-PARENT`

- Probes:
  ```bash
  PYTHON=python3.11 bash scripts/check_local_box_baseline.sh
  bash scripts/check_go_live_rules.sh
  ```
- PASS when:
  - both commands return PASS / zero exit status in the bounded validation context.
- FAIL when:
  - either command fails; or
  - parent guardrail posture is no longer satisfied.

## 5) SLI / alert linkage

| Check ID | Supports SLI/SLO | Supports alert rule |
|---|---|---|
| **`SC-HEALTH`** | **`SLI-Avail`**, **`SLO-1`** | **`AL-AVAIL`** |
| **`SC-OPS`** | supporting visibility for **`SLI-Errors`** and **`SLI-Worker`** | supporting signal for **`AL-ERRORS`**, **`AL-WORKER`** |
| **`SC-WORKER`** | **`SLI-Worker`**, **`SLO-4`** | **`AL-WORKER`** |
| **`SC-PARENT`** | supporting guardrail / release posture, not a customer-facing SLO on its own | supports bounded deployment / rollback safety decisions |

## 6) Minimum completion expectation

Before the Week 3 checklist row can honestly move to **`DONE`**, the following must exist:

1. The synthetic check set is fixed to the V1 surfaces above.
2. A repeatable execution path exists for the probes.
3. Probe PASS / FAIL criteria are explicit.
4. The checks are linked to:
   - agreed SLI/SLO targets; and
   - agreed alert rules / routing expectations.
5. At least one bounded evidence bundle shows the probes being exercised together in stage.

This V1 closes only the **definition / baseline** gap. It does **not** yet prove:

- scheduled automation;
- an external alerting vendor;
- real alert acknowledgement evidence;
- synthetic-check history / dashboard retention;
- live trading readiness.

## 7) Future evidence expectation

The eventual Week 3 **`DONE`** closeout should include at least:

- a bounded check execution record for:
  - **`/health`**
  - **`/ops/state`**
  - worker heartbeat freshness
  - parent guardrail checks
- explicit PASS / FAIL capture
- linkage to alert routing expectations
- at least one real acknowledgement / operator-review record if alert firing is tested

## 8) Boundaries

This document does **not** authorize:

- new monitoring vendors;
- cron installation;
- backend code changes;
- worker behavior changes;
- new external request flows;
- live trading.

Current hard boundary remains:

- **`real external request: NOT AUTHORIZED`**
- **`live trading: NO-GO`**

## 9) Final status

- Critical endpoints defined: YES
- Probe methods explicit: YES
- PASS / FAIL rules explicit: YES
- SLI / alert linkage explicit: YES
- Automation complete: NO
- Real alert acknowledgement evidence complete: NO
- Week 3 synthetic checks row ready to move to DONE by this document alone: NO

## Sign-off

- Baseline V1 author/reviewer: **baolood** / **2026-06-01**
- Current qualification: **solo internal review mode**

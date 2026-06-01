# Service SLI / SLO (Week 3 baseline V1)

**Status:** agreed baseline V1 — availability, latency, and error-rate SLO numbers are now fixed for the current stage/go-live preparation phase. This does **not** mean alert tooling or synthetic checks are complete.

**Owner:** **baolood** (Engineering lead, interim).

**Scope note:** this parent repo orchestrates **`local_box`**, **`anchor-backend/`** (subtree), and **`anchor-console/`** (submodule). This V1 deliberately uses the observability surfaces that already exist today: **`/health`**, **`/ops/state`**, worker heartbeat visibility, and bounded deploy / rollback smoke evidence. It is a minimum agreed baseline, not a final production observability design.

---

## 1) Services in scope (V1)

| Service ID | Description | Entry point (fill when known) |
|------------|-------------|-------------------------------|
| **SVC-API** | HTTP API exposed by **`anchor-backend`** | Stage host local API on `http://127.0.0.1:8000` with observable probes at **`/health`** and **`/ops/state`** |
| **SVC-WORKER** | Async worker processing domain commands | compose service `worker` |
| **SVC-PARENT** | Parent-repo guardrails + `local_box` control plane | `local_box.control.server` (if exposed) |

---

## 2) SLI definitions (agreed V1)

| SLI ID | Signal | Measurement window | Raw definition |
|---------|--------|--------------------|--------------------------------------------------------------|
| **SLI-Avail** | API availability | 30-day rolling | A request is “good” when **`/health`** returns success and the service is reachable on the stage host. Until richer route metrics exist, this SLI is anchored to reachability + success of the current explicit health surface. |
| **SLI-Latency** | API responsiveness | 30-day rolling | Server-side responsiveness judged from the API request path used in deploy / rollback smoke and future synthetic checks; V1 threshold is expressed as a p95 target and will be enforced once the chosen observability stack emits timing series. |
| **SLI-Errors** | Request correctness / service safety | 30-day rolling | Error signal anchored to 5xx responses, failed health/ops smoke, or application-level fatal behavior observed during bounded stage validation and future alerting instrumentation. |
| **SLI-Worker** | Worker liveness | 30-day rolling | Worker is considered alive when the compose service is running and **`/ops/state`** reports a fresh worker heartbeat without panic. |

---

## 3) SLO targets (agreed V1)

| SLO ID | SLI | Target | Error budget (30-day) | Notes |
|--------|-----|--------|---------------------------------------|-------|
| **SLO-1** | SLI-Avail | **99.0%** availability | ~7h 18m monthly unavailability budget | Conservative stage-ready baseline aligned to current single-host topology and existing `/health` probe surface. |
| **SLO-2** | SLI-Latency | **95%** of API checks / requests ≤ **500 ms** (server-side) | Burn when latency target missed | This remains a pragmatic threshold until a fuller metrics stack and capacity profile exist. |
| **SLO-3** | SLI-Errors | **≤ 1.0%** error rate | Shared with availability budget review | Matches the current alerting draft threshold family and avoids pretending we already support tighter production-grade sampling. |
| **SLO-4** | SLI-Worker | Worker heartbeat freshness **≤ 60s** at observation time | Breach when heartbeat stale > 60s | Derived from current `/ops/state` visibility and used to ground worker liveness before richer queue metrics exist. |

**Policy:** no production **M1** launch until these rows are explicitly reviewed again alongside alert routing, synthetic checks, and capacity evidence. V1 is enough to close the Week 3 “Define service SLI/SLO” planning item; it is not the final production observability sign-off.

---

## 4) Observable evidence sources

Current observable sources that back this V1:

- `SVC-API`
  - `GET /health`
  - `GET /ops/state`
- `SVC-WORKER`
  - worker heartbeat visibility through `/ops/state`
  - compose service running state
- deploy / rollback evidence
  - `docs/ONE_COMMAND_DEPLOYMENT_RUNBOOK_FIRST_CONTROLLED_VALIDATION_CLOSEOUT_V1.md`
  - `docs/ROLLBACK_DRILL_FIRST_DESTRUCTIVE_EXECUTION_CLOSEOUT_V1.md`
- alerting draft linkage
  - `docs/ALERTING_ROUTING.md`

This means V1 is backed by real, currently observable surfaces, but not yet by a full metrics backend or alert-rule implementation.

---

## 5) Review cadence

- **Weekly** from first week of Week 3 until M1: compare burn vs budget; open **`docs/GO_LIVE_CHECKLIST.md`** §6 risk if budget **> 50%** consumed with **> 50%** calendar time remaining.
- Revisit V1 targets after:
  - synthetic checks are implemented
  - alert rules are wired and ack-tested
  - capacity testing provides a better latency / degradation envelope

---

## 6) Boundaries

This document does **not** claim:

- final production alerting is complete
- synthetic checks are complete
- metrics backend / dashboards are complete
- live readiness is proven
- real external request is authorized

The following remain true:

- Real external request: NOT AUTHORIZED
- Live trading: NO-GO
- Go-live: NO-GO

---

## 7) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Agreed V1 numbers (Engineering lead): **baolood** / **2026-06-01**
- Agreed V1 numbers (Release manager, interim same-person sign-off): **baolood** / **2026-06-01**

This V1 closes the Week 3 planning item **“Define service SLI/SLO”** in **`docs/GO_LIVE_CHECKLIST.md`**. Later revisions may tighten targets once alerting, synthetic checks, and capacity evidence mature.

# Service SLI / SLO (draft — Week 3)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 3 — **Define service SLI/SLO** until numbers are agreed and signed.

**Owner:** **baolood** (Engineering lead, interim).

**Scope note:** this parent repo orchestrates **`local_box`**, **`anchor-backend/`** (subtree), and **`anchor-console/`** (submodule). SLIs below are **placeholders** — tighten definitions once **stage URLs** and **product-critical paths** are fixed (see **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`**).

---

## 1) Services in scope (v0)

| Service ID | Description | Entry point (fill when known) |
|------------|-------------|-------------------------------|
| **SVC-API** | HTTP API exposed by **`anchor-backend`** | `<https://stage.example/api>` |
| **SVC-WORKER** | Async worker processing domain commands | compose service `worker` |
| **SVC-PARENT** | Parent-repo guardrails + `local_box` control plane | `local_box.control.server` (if exposed) |

---

## 2) SLI definitions (candidates — agree then lock)

| SLI ID | Signal | Measurement window | Raw definition (to be implemented in observability stack) |
|---------|--------|--------------------|--------------------------------------------------------------|
| **SLI-Avail** | Successful responses | 30-day rolling | `good_requests / total_requests` on **SVC-API** health + business-critical routes (list routes in §4 when known) |
| **SLI-Latency** | User-perceived latency | 30-day rolling | `fraction of requests with server-side duration ≤ threshold` (threshold TBD; start with **p95** candidate **500 ms**) |
| **SLI-Errors** | Correctness / safety | 30-day rolling | `5xx + application-level fatal errors / total_requests` |

---

## 3) SLO targets (placeholders — **not agreed** until review)

| SLO ID | SLI | Target | Error budget (30-day, illustrative) | Notes |
|--------|-----|--------|---------------------------------------|-------|
| **SLO-1** | SLI-Avail | **99.9%** | ~43.2 min downtime | Industry default starting point — **lower** if product cannot afford it |
| **SLO-2** | SLI-Latency | **95%** of requests ≤ **500 ms** (server-side) | Burn when latency SLO missed | Tune threshold after load test (**§5 G5**) |
| **SLO-3** | SLI-Errors | **≤ 0.1%** error rate | Coupled with Avail | Define what counts as “good” vs retriable |

**Policy:** no production **M1** launch until these rows are **filled with agreed numbers** and signed by Release manager + Engineering lead (can still be the same person interim, but must be explicit in §8).

---

## 4) Review cadence

- **Weekly** from first week of Week 3 until M1: compare burn vs budget; open **`docs/GO_LIVE_CHECKLIST.md`** §6 risk if budget **> 50%** consumed with **> 50%** calendar time remaining.

---

## 5) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Agreed SLO numbers: pending engineering + product review — replace §3 placeholders and mark **`docs/GO_LIVE_CHECKLIST.md`** Week 3 row `DONE` with link to this commit.

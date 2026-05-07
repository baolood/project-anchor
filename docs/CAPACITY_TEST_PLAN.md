# Capacity + stress test plan (draft — Week 5-6)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 5-6 — **Capacity and stress test** until §3 traffic profile is agreed, §4 dry-run is executed against a real stage host, and §5 degradation behavior is signed off against **`docs/SERVICE_SLI_SLO.md`**.

**Owner:** **baolood** (Engineering lead, interim).

**Pairs with:** **`docs/GO_LIVE_CHECKLIST.md`** §5 **G5** (capacity gate), **`docs/SERVICE_SLI_SLO.md`** (latency / availability SLO is the budget this test consumes), **`docs/STAGE_DEPLOY_RUNBOOK.md`** (target host comes from there), **`docs/ROLLBACK_DRILL_RUNBOOK.md`** (rollback is the safety net if a run goes red).

> Principle: **measure against the SLO**, not against “feels fast”. A capacity run is only meaningful when its pass/fail criteria are stated in the same numbers as **`docs/SERVICE_SLI_SLO.md`**.

---

## 1) Scope

- **In scope:** stage / prod-like deploy of the parent app + worker (per **`docs/STAGE_DEPLOY_RUNBOOK.md`**).
- **Out of scope:** local laptop runs (cannot represent prod IO/CPU); third-party SaaS limits unless captured as a separate row in §6.
- **Pre-test gate:** §5 **G1** (one-command deploy) and **G2** (rollback drill) must already be GREEN — we never load-test a stack we cannot redeploy/rollback.

---

## 2) Test inventory

| Test ID | Type | Goal | Pass criteria (linked to SLO) | Stop condition |
|---------|------|------|--------------------------------|----------------|
| **CT-01** | baseline | establish steady-state at expected RPS | p95 latency under SLO target; 0 5xx | first SLO breach > 1 minute |
| **CT-02** | peak | sustain 1.5× expected peak for 15 min | error rate within SLO error budget | error budget for the day exhausted |
| **CT-03** | stress | ramp until first SLO breach, then hold 5 min | document degradation mode | hard error rate > **5%** or worker stalls |
| **CT-04** | soak | 1× expected RPS for **`<duration>`** (≥ 60 min) | no memory growth slope above **`<MB/min>`** | OOM, restart loops, queue backlog growth |

“`<…>`” entries are filled at sign-off — do not pick numbers without **`docs/SERVICE_SLI_SLO.md`** alignment.

---

## 3) Traffic profile (fill before run)

| Endpoint / job | Share of traffic | Method | Realistic payload size | Notes |
|----------------|-------------------|--------|-------------------------|-------|
| `<endpoint A>` | `<%>` | `GET` | `<bytes>` | |
| `<endpoint B>` | `<%>` | `POST` | `<bytes>` | |
| `<worker job>` | `<jobs/min>` | n/a | `<bytes>` | |

**Expected peak RPS:** `<value>` (source: `<analytics / prod log / estimate>`).

---

## 4) Tooling

- Load generator: **`<k6 | locust | wrk | hey | vendor>`** (pick one, pin version).
- All probes use **`curl --max-time 30`** when verifying steady-state mid-run, matching **`docs/SYNTHETIC_CHECKS.md`** + the curl guardrail in **`scripts/check_checklist_curl_guardrails.sh`**.
- Result storage: artifacts under **`artifacts/go-live/capacity/<date>/`** (gitignored — keep summaries inside **`docs/CAPACITY_TEST_PLAN.md`** §5).

---

## 5) Drill log (run + sign-off table)

| Run ID | Test ID | Date / time | RPS profile | Result vs SLO | Degradation observed | Recovery action |
|--------|---------|-------------|-------------|---------------|----------------------|-----------------|
| `<id>` | CT-01 | | | | | |
| `<id>` | CT-02 | | | | | |
| `<id>` | CT-03 | | | | | |
| `<id>` | CT-04 | | | | | |

Each row must reference the deploy SHA + tag (so a failed run can be paired with **`docs/ROLLBACK_DRILL_RUNBOOK.md`**).

---

## 6) Known limits / dependencies

- Upstream APIs / SaaS quotas: list rate caps and how the test stays under them.
- Database connection pool size and worker concurrency caps — record current values, do not silently raise during a test.
- Cost guard: estimate spend per run (cloud egress / compute) before CT-03 / CT-04.

---

## 7) Acceptance vs go-live board + §5 G5

- **Peak target traffic test completed:** §5 contains at least one **CT-02** row with result vs SLO.
- **Degradation behavior documented:** §5 **CT-03** row has “Degradation observed” + “Recovery action” populated.
- **§5 G5** is GREEN only when both above acceptance items are signed off **and** the run was performed against a stage that already passed §5 **G1** + **G2**.

---

## 8) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Reviewed by (Engineering lead): `<name>` / `<date>`
- Reviewed by (Release manager): `<name>` / `<date>`

When at least CT-02 + CT-03 rows are filled and signed off, update **`docs/GO_LIVE_CHECKLIST.md`** Week 5-6 “Capacity and stress test” row to `DONE` and link **`docs/CAPACITY_TEST_PLAN.md`** + the per-run summaries.

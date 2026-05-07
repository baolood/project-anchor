# Synthetic checks for critical endpoints (draft — Week 3)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 3 — **Synthetic checks for critical endpoints** until probes are deployed against a real stage URL and their ownership is signed off.

**Owner:** **baolood** (Operations lead, interim).

**Pairs with:** **`docs/SERVICE_SLI_SLO.md`** (probes feed SLI-Avail / SLI-Latency), **`docs/ALERTING_ROUTING.md`** (probe failure → alert), **`RUNBOOK.md`**, **`docs/STAGE_DEPLOY_RUNBOOK.md`**.

> Tooling-agnostic. Replace `Tool / scheduler` placeholders with the chosen vendor (e.g. cron + curl, Datadog Synthetics, GitHub Actions on schedule, Grafana Cloud probes). Lock the vendor before Week 3 review so this doc stops being a placeholder.

---

## 1) Probe inventory (critical endpoints)

Fill the **URL** column once stage / prod-like hosts are defined. Until then, treat `<TBD>` as a blocker for `DONE`.

| Probe ID | Target | URL (fill) | Method | Frequency | Success criteria |
|----------|--------|-------------|--------|-----------|--------------------|
| **PR-API-HEALTH** | `anchor-backend` health | `<TBD>/healthz` (or equivalent) | GET | every **1 min** | HTTP 200 within **2 s** |
| **PR-API-CRITICAL** | One business-critical read path | `<TBD>` | GET | every **5 min** | HTTP 200 + payload schema sanity |
| **PR-WORKER-PROGRESS** | Worker liveness signal | metric or status endpoint | poll every **2 min** | progress counter increasing within **5 min** |
| **PR-DEPENDENCY-DB** | Database reachability | `<TBD>` (auth + read-only query) | every **5 min** | round-trip < **2 s** |
| **PR-DEPENDENCY-EXT** | Each upstream dependency the API hard-requires | per dependency | every **5 min** | dependency-defined health |

---

## 2) `curl` policy (mandatory for any probe shell scripts)

If a probe is implemented as a checklist-style shell script, it **must** keep timeout protections (verified by **`scripts/check_checklist_curl_guardrails.sh`**):

```bash
curl --connect-timeout 5 --max-time 20 ...
```

This applies even to "quick local debug" copies; otherwise the parent CI job **`checklist-curl-guardrails`** will fail on push.

---

## 3) Routing failures into alerts

- Probe failure budgets must map to severities defined in **`docs/ON_CALL_SOP.md`**.
- For each probe in §1, declare:
  - **Page severity on N consecutive failures:** `<value>` (start at **3** for 1-min probes, **2** for 5-min probes).
  - **Alert rule binding:** matches a row in **`docs/ALERTING_ROUTING.md`** §2 (e.g. **PR-API-HEALTH** → **AL-AVAIL**).

If a probe is not wired to an alert rule, it is **monitoring**, not protection — call that out explicitly in §5 deltas.

---

## 4) Local sanity check (until tool is chosen)

A minimal, repeatable sanity check you can run right now (after stage URL exists). Replace `<URL>`:

```bash
curl --connect-timeout 5 --max-time 20 -sSf <URL>/healthz >/dev/null && echo HEALTHZ_OK
```

This is **not** a synthetic check; it is the smallest fact you can verify by hand to prove the URL is alive before wiring tooling.

---

## 5) Acceptance vs go-live board

- **Basic probes + dependency checks active:** every row in §1 has a live probe in the chosen tool, and §3 routing is in place.
- **Tool chosen + scheduled:** column "Tool / scheduler" recorded for each probe (single shared scheduler is fine).
- Both must be GREEN to flip **`docs/GO_LIVE_CHECKLIST.md`** Week 3 row to `DONE`. **§5 G2** (P0/P1 alerting verified) cannot be GREEN without §3 routing here being live.

---

## 6) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Reviewed by (Engineering lead): `<name>` / `<date>`
- Reviewed by (Operations lead): `<name>` / `<date>`

When probes are scheduled, paging is wired, and the §1 URL column is filled, link the live probe dashboard / tool URL here and update **`docs/GO_LIVE_CHECKLIST.md`** Week 3 row to `DONE`.

# Alerting + routing (Week 3 closeout-backed V1)

**Status:** closeout-backed V1 — signal sources, severities, thresholds, routing expectations, concrete Telegram P0/P1 delivery, and first bounded ack evidence are now present. Week 3 alerting may be treated as `DONE` for the current go-live preparation scope.

**Owner:** **baolood** (Operations lead, interim).

**Pairs with:** **`docs/SERVICE_SLI_SLO.md`** (SLOs feed alert thresholds), **`docs/ON_CALL_SOP.md`** (severity → response), **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 3 + §5 **G2**.

> Tooling was initially left open on purpose. That gap is now closed for the
> current scope: Telegram is the accepted P0/P1 path, GitHub issue + manual ops
> log is the accepted P2/P3 path, and first bounded ack evidence is recorded in
> **`docs/ALERT_PLATFORM_FIRST_TEST_ALERT_EXECUTION_CLOSEOUT_V1.md`**.

---

## 1) Current signal surfaces

Current signals already observable in the project:

- `SVC-API`
  - `GET /health`
  - `GET /ops/state`
- `SVC-WORKER`
  - worker heartbeat freshness via `/ops/state`
  - compose service running state visible during deploy / rollback validations
- `SVC-DEPLOY`
  - `local-box-baseline` CI status on PRs and `main`

These surfaces are enough to define minimum alert rules now, even though the final delivery tool is not yet chosen.

---

## 2) Routing matrix (V1 expectation)

| Severity (per **`docs/ON_CALL_SOP.md`**) | Channel | Tool / target (fill) | Ack target |
|------------------------------------------|---------|----------------------|------------|
| **P0** | Page primary, then escalate per SOP | **Telegram**; primary target = **baolood** | **5 min** |
| **P1** | Page primary | **Telegram**; primary target = **baolood** | **15 min** |
| **P2** | Chat / ticket | **GitHub issue + manual ops log**; fallback owner = **baolood** | **1 h** |
| **P3** | Ticket / backlog item | **GitHub issue / backlog log** | next business day |

**Current qualification:** `solo internal review mode`. This still does not
claim multi-person paging is live, but it does mean the current single-operator
go-live preparation scope now has a concrete tool target and a real ack record.

**Auto-escalation rule:** if a paging alert is unacked past its target, automatically escalate to the configured backup/escalation contact (and CC the engineering lead for P0). Verify this at the tool level later; do not rely on humans noticing.

---

## 3) Alert rule candidates (agreed V1 thresholds)

These are the minimum rules that must exist before Week 3 sign-off. Thresholds are now aligned to **`docs/SERVICE_SLI_SLO.md`** V1 and current observable surfaces.

| Rule ID | Signal source | Trigger condition | Severity | Notes |
|---------|----------------|------------------------------------|----------|-------|
| **AL-AVAIL** | `SVC-API` health / availability SLO | `/health` unreachable or equivalent availability breach against **99.0%** baseline | **P1** (P0 if total outage) | P0 when API becomes totally unavailable. |
| **AL-LATENCY** | `SVC-API` latency SLO | p95 latency **> 500 ms** for 10 min once latency series exists | **P2** (P1 if 30 min sustained) | Keep as declared threshold even before tooling binds it. |
| **AL-ERRORS** | `SVC-API` error SLO | error rate **> 1.0%** for 5 min | **P1** | Aligns to current V1 error-rate SLO. |
| **AL-WORKER** | worker heartbeat / liveness | heartbeat stale **> 60s** or worker crash/stuck signal for **> 5 min** | **P1** | Derived from `/ops/state` heartbeat and compose visibility. |
| **AL-DEPLOY** | CI / release | Push to `main` while CI red; or revert needed | **P2** | Cross-link with **`docs/RELEASE_BRANCH_POLICY.md`** |

---

## 4) Minimum implementation expectation

This row is now supported by:

1. one concrete tool/target for P0/P1 paging: Telegram
2. one concrete target for P2/P3 routing: GitHub issue + manual ops log
3. runtime wiring of Telegram env into backend / worker containers
4. one real bounded ack evidence bundle

The closeout record for the bounded Telegram proof is:
**`docs/ALERT_PLATFORM_FIRST_TEST_ALERT_EXECUTION_CLOSEOUT_V1.md`**.

---

## 5) Required test before sign-off

Completed bounded proof for current scope:

1. one bounded P1-style Telegram test alert path was fired
2. operator confirmed Telegram message receipt
3. acceptance record was written on the stage host
4. no secret values were exposed during the proof

**Evidence used for `DONE`:** operator-confirmed message receipt plus host-side
acceptance record, summarized in
**`docs/ALERT_PLATFORM_FIRST_TEST_ALERT_EXECUTION_CLOSEOUT_V1.md`**.

---

## 6) Acceptance vs go-live board

- **Critical alerts route to on-call:** GREEN
- **Alert test fired and acknowledged:** GREEN
- Week 3 row may now be flipped to `DONE`, and **§5 G2** may also be marked
  GREEN for current Project Anchor scope.

---

## 7) Boundaries

This V1 still does **not** claim:

- broader multi-operator paging hardening beyond current scope
- auto-escalation proof beyond the accepted current solo-operator path
- real external request is authorized
- live trading is authorized

The following remain true:

- Real external request: NOT AUTHORIZED
- Live trading: NO-GO
- Go-live: NO-GO

---

## 8) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Hardened V1 review (Engineering lead): **baolood** / **2026-06-01**
- Hardened V1 review (Operations lead, interim same-person sign-off): **baolood** / **2026-06-01**
- Telegram alert acceptance closeout: **baolood** / **2026-06-01**

Closeout evidence:
- **`docs/ALERT_PLATFORM_FIRST_TEST_ALERT_EXECUTION_CLOSEOUT_V1.md`**
- host acceptance record:
  **`/root/project-anchor/TELEGRAM_ALERT_ACCEPTANCE_20260601-143247.txt`**

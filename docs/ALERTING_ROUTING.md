# Alerting + routing (Week 3 baseline V1)

**Status:** hardened baseline V1 — signal sources, severities, thresholds, and routing expectations are now explicit. This row is still not `DONE` until a concrete tool/target is chosen and a real alert ack is captured.

**Owner:** **baolood** (Operations lead, interim).

**Pairs with:** **`docs/SERVICE_SLI_SLO.md`** (SLOs feed alert thresholds), **`docs/ON_CALL_SOP.md`** (severity → response), **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 3 + §5 **G2**.

> Tooling-agnostic on purpose. This V1 defines the minimum rules and routing intent using surfaces that already exist today. A later step must bind them to a concrete paging/chat/ticket tool before Week 3 can be closed.

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
| **P0** | Page primary, then escalate per SOP | **TBD tool**; primary target = **baolood** | **5 min** |
| **P1** | Page primary | **TBD tool**; primary target = **baolood** | **15 min** |
| **P2** | Chat / ticket | **TBD tool/channel**; fallback owner = **baolood** | **1 h** |
| **P3** | Ticket / backlog item | **TBD queue** | next business day |

**Current qualification:** `solo internal review mode`. That means V1 can define who should be paged/escalated, but it does **not** claim multi-person paging is already live. The final Week 3 sign-off still requires a concrete tool target and a real ack record.

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

Before this row can be marked `DONE`, the project must have:

1. one concrete tool/target for P0/P1 paging
2. one concrete target for P2/P3 routing
3. alert rules wired to the chosen tool
4. one real ack evidence bundle

This V1 is intentionally a docs-first implementation baseline. It means the semantics are no longer placeholder-only, even though the actual tool hookup is still pending.

---

## 5) Required test before sign-off

1. Fire a synthetic test alert per severity **P0** and **P1**.
2. Confirm the **paging tool** shows it landing on the **on-call primary** within target.
3. Acknowledge from the primary device; record the ack screenshot or audit log.
4. Repeat with primary **unreachable** (silence pager) to verify auto-escalation reaches the backup.

**Evidence required for `DONE`:** ack timestamp(s) + escalation log + a link to the live rule definitions in the chosen tool.

---

## 6) Acceptance vs go-live board

- **Critical alerts route to on-call:** matrix in §1 implemented in tool; rules in §2 deployed.
- **Alert test fired and acknowledged:** §3 evidence captured.
- Both must be GREEN to flip **`docs/GO_LIVE_CHECKLIST.md`** Week 3 row to `DONE`. **§5 G2** (P0/P1 alerting verified) cannot be GREEN before this row is.

---

## 7) Boundaries

This V1 does **not** claim:

- a paging/chat vendor has already been selected
- alert rules are already live in a tool
- ack evidence already exists
- Week 3 alerting is complete
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

When tool, rules, and ack evidence are in place, link the commit / tool URL here and update **`docs/GO_LIVE_CHECKLIST.md`** Week 3 row to `DONE`.

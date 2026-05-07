# Alerting + routing (draft — Week 3)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 3 — **Alert rules + routing implemented** until rules ship in the observability stack and a real test alert is acknowledged.

**Owner:** **baolood** (Operations lead, interim).

**Pairs with:** **`docs/SERVICE_SLI_SLO.md`** (SLOs feed alert thresholds), **`docs/ON_CALL_SOP.md`** (severity → response), **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 3 + §5 **G2**.

> Tooling-agnostic on purpose. Replace the `Tool / channel` columns with concrete vendors (e.g. PagerDuty, Opsgenie, Grafana OnCall, Slack webhooks) when picked. Lock vendor choice **before** Week 3 review so this doc stops being a placeholder.

---

## 1) Routing matrix

| Severity (per **`docs/ON_CALL_SOP.md`**) | Channel | Tool / target (fill) | Ack target |
|------------------------------------------|---------|----------------------|------------|
| **P0** | Page primary, then escalate per SOP | `<pager URL / phone>` | **5 min** |
| **P1** | Page primary | `<pager URL>` | **15 min** |
| **P2** | Chat / ticket | `<chat channel / queue>` | **1 h** |
| **P3** | Ticket | `<queue>` | next business day |

**Auto-escalation rule:** if a paging alert is unacked past its target, automatically page the **on-call backup** (and CC the **engineering lead** for P0). Verify this is configured at the tool level — do not rely on humans noticing.

---

## 2) Alert rule candidates (initial set)

These are the rules that must exist before Week 3 sign-off. Thresholds are placeholders; align with **`docs/SERVICE_SLI_SLO.md`** §3 once SLOs are agreed.

| Rule ID | Signal source | Trigger condition (placeholder) | Severity | Notes |
|---------|----------------|------------------------------------|----------|-------|
| **AL-AVAIL** | SLI-Avail (per **SERVICE_SLI_SLO.md**) | Availability **< 99%** over 5 min on **SVC-API** | **P1** (P0 if total outage) | Promote to P0 when error budget burn rate ≥ 14× |
| **AL-LATENCY** | SLI-Latency | p95 latency **> 500 ms** for 10 min | **P2** (P1 if 30 min sustained) | Threshold revisits after load test (**§5 G5**) |
| **AL-ERRORS** | SLI-Errors | 5xx rate **> 1%** for 5 min | **P1** | Correlate with deploy SHA in alert payload |
| **AL-WORKER** | `worker` health | Worker stuck (no progress / crash loop) for **> 5 min** | **P1** | Use compose / process supervision signal |
| **AL-DEPLOY** | CI / release | Push to `main` while CI red; or revert needed | **P2** | Cross-link with **`docs/RELEASE_BRANCH_POLICY.md`** |

---

## 3) Required test before sign-off

1. Fire a synthetic test alert per severity **P0** and **P1**.
2. Confirm the **paging tool** shows it landing on the **on-call primary** within target.
3. Acknowledge from the primary device; record the ack screenshot or audit log.
4. Repeat with primary **unreachable** (silence pager) to verify auto-escalation reaches the backup.

**Evidence required for `DONE`:** ack timestamp(s) + escalation log + a link to the live rule definitions in the chosen tool.

---

## 4) Acceptance vs go-live board

- **Critical alerts route to on-call:** matrix in §1 implemented in tool; rules in §2 deployed.
- **Alert test fired and acknowledged:** §3 evidence captured.
- Both must be GREEN to flip **`docs/GO_LIVE_CHECKLIST.md`** Week 3 row to `DONE`. **§5 G2** (P0/P1 alerting verified) cannot be GREEN before this row is.

---

## 5) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Reviewed by (Engineering lead): `<name>` / `<date>`
- Reviewed by (Operations lead): `<name>` / `<date>`

When tool, rules, and ack evidence are in place, link the commit / tool URL here and update **`docs/GO_LIVE_CHECKLIST.md`** Week 3 row to `DONE`.

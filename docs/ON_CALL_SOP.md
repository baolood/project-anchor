# On-call SOP (draft — Week 2)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 2 — **On-call SOP draft complete** until reviewed and signed.

**Owner:** **baolood** (On-call primary, interim — same person holds backup until roster expands).

**Related:** **`RUNBOOK.md`**, **`docs/GO_LIVE_CHECKLIST.md`** §6 Risk Register, **`docs/STAGE_DEPLOY_RUNBOOK.md`**, **`docs/ROLLBACK_DRILL_RUNBOOK.md`**.

---

## 1) Incident severity matrix

| Level | User / business impact | Response target | Examples |
|-------|------------------------|-----------------|----------|
| **P0** | Total outage or unbounded financial / safety risk | Page immediately; all hands until mitigated | API down; worker runaway; data corruption suspected |
| **P1** | Major degradation; no safe workaround for core flow | Page within **15 min**; war room optional | Elevated error rate; single AZ down; risk limits mis-applied |
| **P2** | Partial degradation; workaround exists | Ack within **1 h**; fix within business day | Slow queries; non-critical UI; flaky job |
| **P3** | Cosmetic / internal tooling | Next business day | Docs typo; dev-only annoyance |

**Default assumption:** anything touching **money, risk limits, or customer-facing API** starts at **P1** until downgraded with evidence.

---

## 2) Roles and escalation

| Order | Role | Default assignee (interim) | Responsibility |
|-------|------|---------------------------|------------------|
| 1 | **On-call primary** | **baolood** | Triage, first mitigation, comms owner |
| 2 | **On-call backup** | **baolood** (same until split) | Take over if primary unreachable **within 15 min** |
| 3 | **Engineering lead** | **baolood** | Code / infra decisions, rollback approval |
| 4 | **Release manager** | **baolood** | Go/no-go on risky changes mid-incident |
| 5 | **Security owner** | **baolood** | Suspected breach, credential leak, abuse |

**Escalation rule:** if P0/P1 is not **acknowledged** within the response target, escalate **one level** automatically (primary → backup → engineering lead). Log each hop with timestamp in the incident doc.

---

## 3) First-response checklist (all severities)

1. **Stabilize** — stop bleeding (disable feature flag, scale, block traffic, freeze deploys — pick what fits).
2. **Communicate** — open incident thread; post **severity + impact + ETA unknown/known**.
3. **Evidence** — preserve logs, metrics snapshots, `docker compose ps`, recent deploy SHA.
4. **Mitigate** — smallest change that restores safe state (often rollback per **`docs/ROLLBACK_DRILL_RUNBOOK.md`**).
5. **Follow-up** — root cause + action items within **5 business days** for P0/P1.

---

## 4) Notification templates

### Initial post (copy, fill `<>`)

```text
[INCIDENT] <P0|P1|P2|P3> | <one-line summary>
Impact: <who/what is broken>
Started: <UTC time>
Primary: @baolood (interim)
Status: investigating | mitigating | monitoring | resolved
Deploy SHA / tag: <value or unknown>
Next update in: <minutes> or "when we know more"
```

### Hourly update (P0/P1 while active)

```text
[INCIDENT UPDATE] <id> | +<elapsed>
What we tried: <short>
Current state: <user-visible state>
Next: <next action or ETA>
```

---

## 5) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Reviewed by (Release manager): `<name>` / `<date>` — when staffing splits, require a second human here

When the matrix and escalation table are reviewed, update **`docs/GO_LIVE_CHECKLIST.md`** Week 2 row to `DONE` and link the commit or ticket with review notes.

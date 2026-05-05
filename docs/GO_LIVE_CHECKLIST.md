# Go-Live Checklist (Execution Plan)

This checklist is designed for `project-anchor` from current "engineering hardening complete" status to production go-live.

Use this file as the single execution board:
- assign owner for each item
- update status daily
- attach evidence links
- do not mark complete without evidence

---

## 0) Milestone Targets

- **M0 — Internal beta ready (target: 2-4 weeks)**  
  Core flows stable, deployment + rollback validated, on-call simulation done.
- **M1 — Production ready (target: 6-10 weeks)**  
  SLOs, alerting, backup/recovery drill, security and capacity gates all passed.

---

## 1) Governance Rules

- Status values: `TODO | IN_PROGRESS | BLOCKED | DONE`
- Every `DONE` must include evidence (run output, screenshot, link, log excerpt)
- Any `BLOCKED` must include unblock owner and ETA
- Weekly go/no-go review owned by release manager

---

## 2) This Week Kickstart (Day 1-5)

Use this if you want immediate execution without waiting for a full planning meeting.

- [ ] **Day 1 — Assign owners + freeze scope**
  - Confirm owner for each Week 1 item
  - Mark non-go-live work as out-of-scope for this cycle
  - Evidence: owner map link

- [ ] **Day 2 — Go/No-Go gate draft**
  - Write explicit hard-stop release gates
  - Name final go/no-go approver
  - Evidence: gate doc link

- [ ] **Day 3 — Environment parity diff**
  - Produce dev/stage/prod-like config diff
  - Flag high-risk mismatches
  - Evidence: parity diff link

- [ ] **Day 4 — Stage deploy + rollback rehearsal booking**
  - Dry-run deploy from clean checkout
  - Book rollback drill window with owner/on-call
  - Evidence: run output + calendar link

- [ ] **Day 5 — Weekly review and blocker burn-down**
  - Review Week 1 status (`DONE`/`BLOCKED`)
  - Re-assign blockers with ETA before next week starts
  - Evidence: review notes link

---

## 3) Weekly Plan (Fill Owner/ETA)

### Week 1 — Release Gate Definition + Environment Baseline

- [ ] **Define go-live gates (hard stop criteria)**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Written list of mandatory gates
    - Explicit go/no-go authority
  - Evidence: `<link>`

- [ ] **Freeze release branch policy**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Branching, tagging, rollback policy documented
  - Evidence: `<link>`

- [ ] **Prod-like environment parity check**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Environment diff report (dev/stage/prod-like)
    - Critical config parity confirmed
  - Evidence: `<link>`


### Week 2 — Deployment + Rollback + Operational Runbooks

- [ ] **One-command deployment runbook validated**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Stage deploy from clean checkout succeeds
    - Duration baseline recorded
  - Evidence: `<link>`

- [ ] **Rollback drill completed**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Roll forward + rollback both tested
    - Recovery under agreed limit
  - Evidence: `<link>`

- [ ] **On-call SOP draft complete**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Incident severity matrix + escalation flow
  - Evidence: `<link>`


### Week 3 — Observability + Alerting + Error Budget

- [ ] **Define service SLI/SLO**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Availability, latency, error-rate SLOs agreed
  - Evidence: `<link>`

- [ ] **Alert rules + routing implemented**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Critical alerts route to on-call
    - Alert test fired and acknowledged
  - Evidence: `<link>`

- [ ] **Synthetic checks for critical endpoints**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Basic probes + dependency checks active
  - Evidence: `<link>`


### Week 4 — Data Safety + Recovery Drill

- [ ] **Backup strategy implemented**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Backup schedule and retention documented
  - Evidence: `<link>`

- [ ] **Restore drill (table-level + full restore)**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Successful restore in test environment
    - RPO/RTO measured and within target
  - Evidence: `<link>`

- [ ] **Data migration rollback path verified**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - At least one rollback test from migration state
  - Evidence: `<link>`


### Week 5-6 — Security + Capacity + Final Hardening

- [ ] **Secret management and key rotation policy**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - No plaintext secrets in repo/config
    - Rotation procedure tested
  - Evidence: `<link>`

- [ ] **Permission minimization and audit**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Service/account permissions reviewed and reduced
  - Evidence: `<link>`

- [ ] **Capacity and stress test**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Peak target traffic test completed
    - Degradation behavior documented
  - Evidence: `<link>`


### Week 7-8 — Controlled Launch

- [ ] **Canary/gradual rollout plan executed**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Small traffic slice healthy for agreed period
  - Evidence: `<link>`

- [ ] **Release freeze + go/no-go review**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - All hard gates `DONE`
    - Risk register signed off
  - Evidence: `<link>`

- [ ] **Production launch completed**  
  - Owner: `<name>`  
  - Status: `TODO`  
  - Acceptance:
    - Launch report and post-launch monitoring window closed
  - Evidence: `<link>`

---

## 4) Hard Go/No-Go Gates (Must Be GREEN)

- [ ] Deployment and rollback drills pass
- [ ] P0/P1 alerting verified
- [ ] Backup/restore drill pass (RPO/RTO within target)
- [ ] Security review complete (secrets/permissions/vuln baseline)
- [ ] Capacity test at target load pass
- [ ] On-call roster and incident SOP active

If any item is not green, launch is **NO-GO**.

---

## 5) Daily Standup Template

- Yesterday done:
- Today plan:
- Current blockers:
- Risks (new/changed):
- Need decision from:

---

## 6) Final Go-Live Signoff

- Release manager: `<name>` / `<date>`
- Engineering lead: `<name>` / `<date>`
- Operations lead: `<name>` / `<date>`
- Product owner: `<name>` / `<date>`


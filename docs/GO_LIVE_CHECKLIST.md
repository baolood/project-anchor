# Go-Live Checklist (Execution Plan)

This checklist is designed for `project-anchor` from current "engineering hardening complete" status to production go-live.

Use this file as the single execution board:
- assign owner for each item
- update status daily
- attach evidence links
- do not mark complete without evidence

---

## 0) Milestone Targets

This section is the **canonical statement of intent**. Acceptance items here must trace to checked work below; if any acceptance item is not GREEN by the **target date**, follow the **cutoff rule** (do not silently slip).

### M0 — Internal beta ready

- **Target date:** **2026-05-29** (planning anchor: 2026-05-07)
- **Acceptance (all must be GREEN with evidence):**
  - One-command stage deploy from clean checkout succeeds (§4 Week 2)
  - Rollback drill within agreed recovery limit (§4 Week 2)
  - On-call SOP draft signed off (§4 Week 2)
  - §2 Owner Matrix fully populated
- **Cutoff rule:** if any acceptance item is not GREEN at the target date, declare **NO-GO** for M0, log a row in §6 Risk Register (impact + owner + ETA), and reschedule M0 by exactly **one week** at the next §9 review.

### M1 — Production ready

- **Target date:** **2026-07-10** (planning anchor: 2026-05-07)
- **Acceptance (all must be GREEN with evidence):**
  - All §5 hard gates **G1–G6** GREEN
  - Backup/restore drill within RPO/RTO target (§4 Week 4)
  - Capacity/stress test within agreed degradation envelope (§4 Week 5-6)
  - Security review complete: secrets policy + permission audit (§4 Week 5-6)
  - Final go/no-go signoff captured in §8
- **Cutoff rule:** if any acceptance item is not GREEN at the target date, declare **NO-GO** for M1, log the impacted gate(s) in §6, and rerun §9 review **weekly** until all gates are GREEN or scope is explicitly reduced (recorded in §9 minutes).

---

## 1) Governance Rules

- Status values: `TODO | IN_PROGRESS | BLOCKED | DONE`
- Every `DONE` must include evidence (run output, screenshot, link, log excerpt)
- Any `BLOCKED` must include unblock owner and ETA
- Weekly go/no-go review owned by release manager
- **Operational rules (SSOT):** **`docs/RULES.md`** is the canonical contract for **`go_live_status_report.sh`** (**stdout-only** in CI vs **`--out`** file path locally). **`scripts/check_go_live_rules.sh`** enforces anchors in that file; update both together if you change machine-verifiable wording.
- **CI coupling:** workflow **`local-box-baseline`** runs **`./scripts/go_live_status_report.sh`** on every push/PR (**CI: stdout only**; **local standup evidence:** **`--out`** with a **file** path — see **`./scripts/go_live_status_report.sh --help`**). This exact path (**`docs/GO_LIVE_CHECKLIST.md`**) is also listed in **`scripts/check_local_box_baseline.sh`** (`REQUIRED_PATHS`) — do not rename/move this file without updating that script (and the default **`CHECKLIST_FILE`** in **`go_live_status_report.sh`** if you change conventions). Do not overhaul status-marker conventions without updating the reporter script. After substantive edits here, run **`./scripts/go_live_status_report.sh`** locally before merge.
- **CI triage:** the workflow has two jobs — **`checklist-curl-guardrails`** (curl policy only) and **`check`** (Python install, baseline, go-live reporter, smokes). Each job sets **`timeout-minutes`** in **`.github/workflows/local-box-baseline.yml`**. Job **`check`** restores a **pip** cache via **`actions/setup-python`** keyed on **`requirements.txt`** and **`requirements.in`**. See root **`README.md`** (CI section) and **`RUNBOOK.md`** (Parent repo CI) for repro order and context. To list or gate recent runs from your laptop, install **`gh`**, run **`gh auth login`**, then use **`./scripts/check_local_box_ci_runs.sh`** (examples in **`README.md`** CI). With **`--branch`**, the script forwards **`gh run list --branch`** so the newest runs for that branch are not lost inside a global **`--limit`** window. **`--failed-only`** lists completed runs that are not success (and not cancelled — useful when cancel-in-progress hides noise). **`--cancelled-only`** / **`--canceled-only`** and **`--failed-only`** cannot be combined. (`--fail-on-cancelled` also supports alias `--fail-on-canceled`.) For strict branch gates, combine **`--latest-only --fail-on-failed`** (alias: **`--fail-on-non-success`**). Add **`--fail-on-incomplete`** (alias: **`--fail-on-non-completed`**) when you need to fail on runs still in progress/queued. Add **`--fail-on-empty`** when no matching rows should be treated as a hard failure. Shortcut: **`--gate-strict` (alias: `--strict`)** (requires **`--branch`**, implies **`--fail-on-cancelled`** + **`--fail-on-empty`**, and is mutually exclusive with **`--cancelled-only`** / **`--canceled-only`** / **`--failed-only`**). `--summary` and `--json` are mutually exclusive, and `--json` implies quiet text mode so stdout remains machine-readable. Optionally re-trigger from GitHub **Actions** → **local-box-baseline** → **Run workflow** (**`workflow_dispatch`**).

---

## 2) Owner Matrix (Fill First)

**Interim staffing (single maintainer):** all roles below map to **`baolood`** until split across people. Replace names/handles when staffing expands (do not delete the interim note — append the new assignees).

- Release manager: **baolood** (go/no-go chair per §9)
- Engineering lead: **baolood**
- Operations lead: **baolood**
- Security owner: **baolood**
- Data/DB owner: **baolood**
- On-call primary: **baolood**
- On-call backup: **baolood** (use external backup roster when available)

---

## 3) This Week Kickstart (Day 1-5)

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

## 4) Weekly Plan (Fill Owner/ETA)

### Week 1 — Release Gate Definition + Environment Baseline

- [ ] **Define go-live gates (hard stop criteria)**  
  - Owner: **baolood** (Release manager)  
  - Status: `DONE`  
  - Acceptance:
    - Written list of mandatory gates → §5 (gate table **G1–G6**)
    - Explicit go/no-go authority → §9 chair = Release manager (**baolood**)
  - Evidence: §5 (**G1–G6**), §9 template; gate IDs introduced in commit **`fd7d4d8`**

- [ ] **Freeze release branch policy**  
  - Owner: **baolood** (Release manager)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Branching, tagging, rollback policy documented
  - Evidence: **`docs/RELEASE_BRANCH_POLICY.md`** (draft); GitHub branch protection on **`main`** still **OPEN** as **§6 / R-001**

- [ ] **Prod-like environment parity check**  
  - Owner: **baolood** (Operations lead)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Environment diff report (dev/stage/prod-like)
    - Critical config parity confirmed
  - Evidence: **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`** (working copy — fill §5 intentional deltas + sign-off when ready)


### Week 2 — Deployment + Rollback + Operational Runbooks

- [ ] **One-command deployment runbook validated**  
  - Owner: **baolood** (Engineering lead)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Stage deploy from clean checkout succeeds
    - Duration baseline recorded
  - Evidence: **`docs/STAGE_DEPLOY_RUNBOOK.md`** (draft — fill duration table + first validated run sign-off)

- [ ] **Rollback drill completed**  
  - Owner: **baolood** (Operations lead)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Roll forward + rollback both tested
    - Recovery under agreed limit
  - Evidence: **`docs/ROLLBACK_DRILL_RUNBOOK.md`** (draft — fill drill log + post-rollback smoke + agreed recovery target)

- [ ] **On-call SOP draft complete**  
  - Owner: **baolood** (Release manager / on-call primary, interim)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Incident severity matrix + escalation flow
  - Evidence: **`docs/ON_CALL_SOP.md`** (draft — second-human review pending when roster splits)


### Week 3 — Observability + Alerting + Error Budget

- [ ] **Define service SLI/SLO**  
  - Owner: **baolood** (Engineering lead)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Availability, latency, error-rate SLOs agreed
  - Evidence: **`docs/SERVICE_SLI_SLO.md`** (draft — §3 targets are placeholders until review sign-off)

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

## 5) Hard Go/No-Go Gates (Must Be GREEN)

Each gate is a **hard stop**. If any item is not GREEN at the §9 review, launch is **NO-GO** and the §9 decision row records the blocking gate ID(s).

- [ ] **G1 — Deployment and rollback drills pass**
  - Verifier: Operations lead
  - Evidence: stage deploy log + rollback drill log
  - Linked plan: §4 Week 2
- [ ] **G2 — P0/P1 alerting verified (test alert acked)**
  - Verifier: Operations lead
  - Evidence: alert test screenshot + on-call ack log
  - Linked plan: §4 Week 3
- [ ] **G3 — Backup/restore drill within RPO/RTO**
  - Verifier: Data/DB owner
  - Evidence: restore drill log + RPO/RTO measurement vs target
  - Linked plan: §4 Week 4
- [ ] **G4 — Security review complete (secrets + permissions + vuln baseline)**
  - Verifier: Security owner
  - Evidence: review report + audit checklist signoff
  - Linked plan: §4 Week 5-6
- [ ] **G5 — Capacity/stress test at target load pass**
  - Verifier: Engineering lead
  - Evidence: load test report + degradation behavior notes
  - Linked plan: §4 Week 5-6
- [ ] **G6 — On-call roster + incident SOP active**
  - Verifier: Release manager
  - Evidence: roster doc + SOP signoff
  - Linked plan: §4 Week 2 + §4 Week 3

---

## 6) Risk Register (Live Table)

Use one row per active risk; update daily until closed.

- Risk ID: **R-001**
- Description: **`main` branch protection not yet enforced** (merge can bypass required **`local-box-baseline`** checks until GitHub Settings are updated).
- Impact: **High**
- Probability: **High** (until Settings are GREEN)
- Owner: **baolood**
- Mitigation: Follow **`docs/GITHUB_BRANCH_PROTECTION.md`**; after enabling, run **`./scripts/check_local_box_ci_runs.sh --branch main --gate-strict --quiet`** once (requires **`gh auth login`** first). Until **`gh`** is authenticated locally, treat API/CLI verification as **blocked** and use the GitHub **Settings** UI as source of truth.
- Trigger/Signal: PR merged or push landed on **`main`** while protection is off; or CI red on **`main`** without a revert within SLA.
- Status: **OPEN**
- ETA to close: **2026-05-14**

- Risk ID: **R-002**
- Description: **Python version drift** — maintainer machine runs **3.8.10**; CI pins **3.11**. Parent smokes might pass locally but break in CI (or vice versa) when 3.9+ syntax / stdlib is introduced.
- Impact: **Medium**
- Probability: **Medium**
- Owner: **baolood**
- Mitigation: Install Python **3.11** locally (e.g. via `pyenv` or system installer) and re-run **`./scripts/check_local_box_baseline.sh`** + smokes; until then, treat **CI** as source of truth for parent Python tests and avoid claiming "works on my machine" before CI is GREEN.
- Trigger/Signal: CI failure that does not reproduce locally (or local pass that CI rejects); contribution adds 3.9+-only constructs.
- Status: **OPEN**
- ETA to close: **2026-05-21**

---

## 7) Daily Standup Template

- Machine snapshot (run before standup, attach or paste path):
  - **Recommended evidence path (standup / audit trail):** `artifacts/go-live/go_live_daily_status_YYYY-MM-DD.out` (tracked onboarding for this folder: `artifacts/go-live/README.md`)
  - **Recommended commands:**
    - `mkdir -p artifacts/go-live` (optional — the reporter creates parent dirs for `--out` if missing)
    - `./scripts/go_live_status_report.sh --out artifacts/go-live/go_live_daily_status_$(date +%F).out`
  - **`--out`** must be a file path (directory targets are rejected).
  - In **`local-box-baseline`**, the reporter step runs with no **`--out`** argument (workflow log captures stdout); keep using **`--out`** locally for **`artifacts/go-live/*.out`** as above.
  - **Temporary local check only:** `/tmp` is fine for ad-hoc debugging (for example `./scripts/go_live_status_report.sh --out /tmp/go_live_daily_status.out`); it is not a durable standup artifact location.
  - **Git policy:** daily `.out` files are **run artifacts** — **do not commit them by default**. Repository **`.gitignore` ignores `artifacts/go-live/*.out`**. If you need a curated sample in git, use a different filename or path and document the exception in the PR.
- Yesterday done:
- Today plan:
- Current blockers:
- Risks (new/changed):
- Need decision from:

---

## 8) Final Go-Live Signoff

- Release manager: `<name>` / `<date>`
- Engineering lead: `<name>` / `<date>`
- Operations lead: `<name>` / `<date>`
- Product owner: `<name>` / `<date>`

---

## 9) Go/No-Go Review Template

Use this section in the final review meeting.

- Review date/time: `<YYYY-MM-DD HH:MM>`
- Release target window: `<window>`
- Chair (decision owner): **baolood** (Release manager per §2 — update if delegated)
- Participants: `<names>`

### Gate results

- Deployment + rollback drill: `PASS|FAIL` (evidence: `<link>`)
- Alerting + routing: `PASS|FAIL` (evidence: `<link>`)
- Backup/restore drill: `PASS|FAIL` (evidence: `<link>`)
- Security checks: `PASS|FAIL` (evidence: `<link>`)
- Capacity/stress checks: `PASS|FAIL` (evidence: `<link>`)
- On-call readiness: `PASS|FAIL` (evidence: `<link>`)

### Decision

- Final decision: `GO | NO-GO`
- If `NO-GO`, top blockers + owner + ETA:
  1. `<blocker>` / `<owner>` / `<eta>`
  2. `<blocker>` / `<owner>` / `<eta>`

---

## 10) Launch Week Run Sheet (T-7 to T+1)

- [ ] **T-7 to T-5:** freeze feature scope, finalize owner matrix, confirm rollout window
- [ ] **T-4 to T-3:** rerun deployment + rollback drill in stage
- [ ] **T-2:** verify alerts, on-call roster, escalation contacts
- [ ] **T-1:** final go/no-go review and signoff
- [ ] **T (launch):** canary rollout + watch SLO/alerts for agreed window
- [ ] **T+1:** post-launch review, open follow-up actions, close launch ticket


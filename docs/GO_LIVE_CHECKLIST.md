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

### Current critical path (rolling)

**Single convergence point:** a **stage / prod-like host** (URL + deploy target agreed and recorded in **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`** §5) is the prerequisite that turns the Week 2–6 **`IN_PROGRESS`** runbooks from drafts into **`DONE`** (deploy, rollback, observability, backup/restore, capacity, secrets drills all execute against the same place).

**Do this week:** stand up or lock that target host first; parallel track: close **§6 / R-001** (**`docs/GITHUB_BRANCH_PROTECTION.md`**) so merges cannot bypass CI.

**WIP discipline:** do not open new §4 **`IN_PROGRESS`** work until an existing row moves to **`DONE`** or **`BLOCKED`** with owner + ETA — see **`docs/RULES.md`** (**WIP cap** + **WIP freeze**).

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

- [x] **Freeze release branch policy**
  - Owner: **baolood** (Release manager)  
  - Status: `DONE`
  - Acceptance:
    - Branching, tagging, rollback policy documented
  - Evidence: **`docs/RELEASE_BRANCH_POLICY.md`** (active); **`enforce_admins.enabled = true`** on **`main`**; PR-only path verified before enforcement by PR **#13** and after enforcement by PR **#14** / PR **#15**

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

- [x] **On-call SOP draft complete**
  - Owner: **baolood** (Release manager / on-call primary, interim)  
  - Status: `DONE`
  - Acceptance:
    - Incident severity matrix + escalation flow
  - Evidence: **`docs/ON_CALL_SOP.md`** (active interim draft-complete baseline — severity matrix + escalation flow present; current qualification: **solo internal review mode**; second-human review pending when roster splits)


### Week 3 — Observability + Alerting + Error Budget

- [ ] **Define service SLI/SLO**  
  - Owner: **baolood** (Engineering lead)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Availability, latency, error-rate SLOs agreed
  - Evidence: **`docs/SERVICE_SLI_SLO.md`** (draft — §3 targets are placeholders until review sign-off)

- [ ] **Alert rules + routing implemented**  
  - Owner: **baolood** (Operations lead)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Critical alerts route to on-call
    - Alert test fired and acknowledged
  - Evidence: **`docs/ALERTING_ROUTING.md`** (draft — vendor + rule deployment + test alert ack pending)

- [ ] **Synthetic checks for critical endpoints**  
  - Owner: **baolood** (Operations lead)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Basic probes + dependency checks active
  - Evidence: **`docs/SYNTHETIC_CHECKS.md`** (draft — fill probe URLs + tool/scheduler + routing wiring)


### Week 4 — Data Safety + Recovery Drill

- [ ] **Backup strategy implemented**  
  - Owner: **baolood** (Data/DB owner)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Backup schedule and retention documented
  - Evidence: **`docs/BACKUP_AND_RECOVERY.md`** (draft — fill §2 schedule/retention + §4 verification evidence)

- [ ] **Restore drill (table-level + full restore)**  
  - Owner: **baolood** (Data/DB owner)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Successful restore in test environment
    - RPO/RTO measured and within target
  - Evidence: **`docs/RESTORE_DRILL_RUNBOOK.md`** (draft — fill drill A/B tables + §4 RPO/RTO measurements)

- [ ] **Data migration rollback path verified**  
  - Owner: **baolood** (Data/DB owner)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - At least one rollback test from migration state
  - Evidence: **`docs/MIGRATION_ROLLBACK_RUNBOOK.md`** (draft — choose S1/S2/S3 + fill §3 drill log)


### Week 5-6 — Security + Capacity + Final Hardening

- [ ] **Secret management and key rotation policy**  
  - Owner: **baolood** (Security owner)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - No plaintext secrets in repo/config
    - Rotation procedure tested
  - Evidence: **`docs/SECRETS_AND_ROTATION.md`** (draft — fill §1 inventory + §2 scan + §4 rehearsal)

- [ ] **Permission minimization and audit**  
  - Owner: **baolood** (Security owner)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Service/account permissions reviewed and reduced
  - Evidence: **`docs/PERMISSION_AUDIT.md`** (draft — fill §1 inventory + §3 reduction rows with before/after)

- [ ] **Capacity and stress test**  
  - Owner: **baolood** (Engineering lead)  
  - Status: `IN_PROGRESS`  
  - Acceptance:
    - Peak target traffic test completed
    - Degradation behavior documented
  - Evidence: **`docs/CAPACITY_TEST_PLAN.md`** (draft — fill §3 traffic profile, run §2 CT-02 + CT-03 against stage, log §5)


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
- Description: **`main` branch protection enforced for admins** — required status checks remain configured and verified by CLI, and **`enforce_admins`** is now enabled so admin direct-push bypass is no longer accepted on **`main`**.
- Impact: **High** (admin push can land code without CI gate)
- Probability: **Low** (post-enforcement PR path has been re-verified; direct admin bypass is no longer the default operating mode)
- Owner: **baolood**
- Mitigation: Follow **`docs/GITHUB_BRANCH_PROTECTION.md`**; keep **`enforce_admins`** enabled, keep required checks **`check`** and **`checklist-curl-guardrails`** present, and verify future main changes continue to arrive through the PR path. **`gh`** is authenticated locally — API/CLI triage is **unblocked**.
- **API verification record (local, 2026-05-31):** **`gh api repos/baolood/project-anchor/branches/main/protection`** returned: **`required_status_checks.strict = true`**, **`required_status_checks.contexts = ["check", "checklist-curl-guardrails"]`** (both checks tied to **GitHub Actions** app id **`15368`**), **`required_pull_request_reviews.required_approving_review_count = 0`**, and **`enforce_admins.enabled = true`** — i.e. admin bypass is now removed from the accepted main workflow posture.
- **CLI verification record (local, 2026-05-07):** `gh auth status` — logged in to github.com as **baolood** (HTTPS, scopes: `gist read:org repo workflow`). **`./scripts/check_local_box_ci_runs.sh --branch main --limit 5 --gate-strict`** — **PASS** (latest run **`25491239855`** on **`main`**, `completed` / `success`).
- **Closure state:** **`enforce_admins`** has now been enabled and the PR-only path has been re-verified after enforcement, so the admin-bypass risk tracked by **R-001** is considered closed. This does **not** authorize go-live, real external request, or live trading.
- Trigger/Signal: any future branch protection drift that disables **`enforce_admins`**, removes required checks, disables **`strict = true`**, or demonstrates that admin direct-push bypass has become possible again on **`main`**.
- Status: **DONE**
- Closed on: **2026-05-31**
- Close evidence: **`enforce_admins.enabled = true`**; required checks **`check`** and **`checklist-curl-guardrails`** remain configured with **`strict = true`**; post-enforcement PR path verified by PR **#14**; main **`local-box-baseline`** run **`26701688720`** completed **success** on merge commit **`92801fb`**.
- ETA to close: **CLOSED**
- Review note: R-001 is closed for the admin-bypass risk only; §9 retains the evidence trail, and go-live still requires separate blocker clearance.

- Risk ID: **R-002**
- Description: **Python version drift** — local Python **3.11.15** is now available at **`/opt/homebrew/bin/python3.11`** and has been used to run the parent baseline successfully. The earlier local drift concern is closed for the current go-live checklist scope.
- Impact: **Medium**
- Probability: **Low**
- Owner: **baolood**
- Mitigation: keep using **`python3.11`** for parent baseline/smoke checks when local evidence is required, and continue treating CI as the final source of truth.
- Trigger/Signal: CI failure that does not reproduce locally, local pass that CI rejects, or loss/removal of the local **python3.11** runtime.
- Status: **DONE**
- Closed on: **2026-05-30**
- Close evidence: local **`PYTHON=python3.11 bash scripts/check_local_box_baseline.sh`** PASS; local **`bash scripts/check_go_live_rules.sh`** PASS; GitHub Actions **`local-box-baseline`** run **`26680725818`** completed **success** for commit **`e729525023684eb2642e60589206d11cc3ad37c4`**.

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

### Recorded §9 reviews (append-only)

#### 2026-05-18 — R-001 / go-live posture

- R-001 §9 outcome: keep blocking go-live
- Status (§6): remain **OPEN** (not closed)
- Decision: **NO-GO** for live trading
- Reason: `main` branch protection remains partially enforced; **`enforce_admins` is still `false`**; no new PR-only / admin-enforcement evidence is available.
- Next action: decide **`enforce_admins` + PR-only** path or continue documented admin bypass.
- Evidence required before close: `gh api` branch protection output + **`local-box-baseline`** green after protection change.
- §6 R-001 ETA: unchanged (**2026-05-21**)
- Note: CI green on **`main`** does **not** imply go-live approval while **R-001** is **OPEN**.

#### 2026-05-22 — R-001 / R-002 ETA review after dry-run main-chain progress

- R-001 §9 outcome: keep blocking go-live
- R-002 §9 outcome: keep blocking go-live
- Status (§6): both remain **OPEN** (not closed)
- Decision: **NO-GO** for live trading
- Reason: dry-run main-chain validation progressed through Trade Gate, proxy, cloud backend, `commands_domain`, worker, risk hard-limit `FAILED`, and small-notional `DONE`; however, branch admin bypass (**R-001**) and local/CI Python version drift (**R-002**) still remain unresolved go-live risks.
- Next action: decide and apply the **`enforce_admins` + PR-only** path for **R-001**; align local Python runtime with CI Python **3.11+** and rerun baseline checks for **R-002**.
- Evidence required before close: branch protection `gh api` output + **`local-box-baseline`** green after protection change for **R-001**; local Python **3.11+** baseline/smoke evidence + CI green for **R-002**.
- §6 R-001 ETA: moved to **2026-05-29**
- §6 R-002 ETA: moved to **2026-05-29**
- Note: dry-run **DONE** and risk **FAILED** path validation does **not** imply go-live approval while **R-001** or **R-002** is **OPEN**.

#### 2026-05-30 — R-001 / R-002 ETA review after runtime-proof hold and guardrail freeze

- R-001 §9 outcome: keep blocking go-live
- R-002 §9 outcome: keep blocking go-live
- Status (§6): both remain **OPEN** (not closed)
- Decision: **NO-GO** for live trading
- Reason: runtime proof docs-only expansion is stopped and guardrail governance expansion is frozen, but branch admin bypass (**R-001**) and local/CI Python version drift (**R-002**) still remain unresolved go-live risks. The current runtime-proof posture remains **HOLD_FOR_REAL_COLLECTION_CONDITIONS**; this does not authorize live trading.
- Next action: decide and apply the **`enforce_admins` + PR-only** path for **R-001**; align local Python runtime with CI Python **3.11+** and rerun baseline checks for **R-002**.
- Evidence required before close: branch protection `gh api` output + **`local-box-baseline`** green after protection change for **R-001**; local Python **3.11+** baseline/smoke evidence + CI green for **R-002**.
- §6 R-001 ETA: moved to **2026-06-06**
- §6 R-002 ETA: moved to **2026-06-06**
- Note: runtime proof hold, dry-run **DONE**, and guardrail governance freeze do **not** imply go-live approval while **R-001** or **R-002** is **OPEN**.

#### 2026-05-30 — R-001 admin enforcement decision after branch protection read-only check

- R-001 §9 outcome: keep blocking go-live
- Status (§6): remain **OPEN** (not closed)
- Decision: **NO-GO** for live trading
- Admin enforcement decision: do **not** enable **`enforce_admins`** in this step.
- PR-only decision: do **not** switch to PR-only in this step.
- Reason: the current terminal-only recovery workflow still depends on direct pushes for small, low-risk documentation fixes. GitHub branch protection read-only check confirms required checks are configured, but **`enforce_admins.enabled = false`**, so admin bypass remains real and accepted as an open risk for now.
- Evidence: branch protection API read-only check showed **`required_status_checks.strict = true`**, required contexts **`check`** and **`checklist-curl-guardrails`**, **`required_approving_review_count = 0`**, and **`enforce_admins.enabled = false`**.
- Next action: keep R-001 open until a separate workflow migration explicitly enables **`enforce_admins`** and removes direct-push reliance.
- §6 R-001 ETA: remains **2026-06-06**
- Note: this decision records the current risk posture; it does not close R-001 and does not authorize real external request or live trading.

#### 2026-05-30 — R-002 Python 3.11 local baseline evidence

- R-002 §9 outcome: close candidate, pending CI confirmation
- Status (§6): remain **OPEN** in this step
- Decision: **NO-GO** for live trading
- Evidence: local **`python3.11`** is available at **`/opt/homebrew/bin/python3.11`** and reports **Python 3.11.15**.
- Evidence: **`PYTHON=python3.11 bash scripts/check_local_box_baseline.sh`** completed **PASS** locally.
- Evidence: **`bash scripts/check_go_live_rules.sh`** completed **PASS** after the Python 3.11 baseline check.
- Reason: the local Python 3.11 path now exists and can run the baseline, reducing R-002 from an unresolved local-runtime availability risk to a close candidate. R-002 is not closed in this step because this record still needs a pushed commit and successful **`local-box-baseline`** CI confirmation.
- Next action: push this record and confirm GitHub Actions **`local-box-baseline`** completes successfully on **`main`**.
- §6 R-002 ETA: remains **2026-06-06**
- Note: Python 3.11 local baseline evidence does not imply go-live approval while R-001 remains **OPEN** and live trading remains **NO-GO**.

#### 2026-05-30 — R-002 close decision after Python 3.11 baseline and CI confirmation

- R-002 §9 outcome: close
- Status (§6): **DONE**
- Decision: **NO-GO** for live trading
- Reason: local **`python3.11`** is available at **`/opt/homebrew/bin/python3.11`** and reports **Python 3.11.15**; **`PYTHON=python3.11 bash scripts/check_local_box_baseline.sh`** completed **PASS**; **`bash scripts/check_go_live_rules.sh`** completed **PASS**; GitHub Actions **`local-box-baseline`** run **`26680725818`** completed **success** on commit **`e729525023684eb2642e60589206d11cc3ad37c4`**.
- Close evidence: local Python 3.11 baseline PASS + go-live rules PASS + CI success.
- Remaining blocker: R-001 remains **OPEN** because admin bypass is still accepted as an open risk.
- Note: closing R-002 does **not** authorize real external request or live trading while R-001 remains **OPEN**.

#### 2026-05-31 — R-001 post-enforcement PR-path verification started
- R-001 §9 outcome: post-enforcement PR-path verification started
- Status (§6): remain **OPEN** in this step
- Decision: **NO-GO** for live trading
- Evidence: **`enforce_admins`** is now enabled on **`main`** while required checks remain **`check`** and **`checklist-curl-guardrails`** with strict status checks still enforced.
- Purpose: verify that a small docs-only branch -> PR -> CI path still works after admin direct-push bypass is removed.
- Boundary: this step does not close R-001, does not authorize real external request, and does not change runtime or live trading posture.

#### 2026-05-31 — R-001 close-decision candidate after PR-only dry run
- R-001 §9 outcome: close decision candidate formed
- Status (§6): remain **OPEN** in this step
- Decision: **NO-GO** for live trading
- Evidence: PR-only workflow has now been proven through branch **push** and **pull_request** CI on **`chore/r001-pr-only-dry-run`** with commit **`3572b3a`** and follow-up docs note **`f253595`**.
- Evidence: branch push CI **`26700385849`** and branch-update push CI **`26700691080`** completed **success**.
- Evidence: PR CI **`26700573569`** and PR-update CI **`26700691732`** completed **success** for PR **#13**.
- Interpretation: the workflow path needed for a future PR-only migration is no longer theoretical; it has now been rehearsed successfully.
- Remaining blocker: **`enforce_admins`** is still **not enabled**, GitHub branch protection has not been changed, and direct push to **`main`** is still technically possible for an admin.
- Next action: make an explicit separate decision on whether to enable **`enforce_admins`** and retire documented direct-push reliance.
- Note: this entry does not close R-001, does not change branch protection, and does not authorize real external request or live trading.

#### 2026-05-31 — R-001 PR-only dry-run workflow passed
- R-001 §9 outcome: PR-only workflow dry run passed
- Status (§6): remain **OPEN** (not closed)
- Decision: **NO-GO** for live trading
- Evidence: branch **`chore/r001-pr-only-dry-run`** was pushed successfully with commit **`3572b3a`**.
- Evidence: GitHub Actions **`local-box-baseline`** run **`26700385849`** completed **success** for the branch **`push`** event.
- Evidence: PR **#13** (**https://github.com/baolood/project-anchor/pull/13**) opened successfully against **`main`**.
- Evidence: GitHub Actions **`local-box-baseline`** run **`26700573569`** completed **success** for the **`pull_request`** event.
- Boundary: this proves branch -> PR -> CI workflow viability only; it does not enable **`enforce_admins`**, does not change GitHub branch protection, and does not close R-001.
- Note: real external request remains **NOT AUTHORIZED** and live trading remains **NO-GO**.

#### 2026-05-30 — R-001 PR-only dry-run branch started
- R-001 §9 outcome: PR-only workflow dry run started
- Status (§6): remain **OPEN** (not closed)
- Decision: **NO-GO** for live trading
- Reason: a local branch **`chore/r001-pr-only-dry-run`** was created to verify that future small documentation changes can move through branch → PR → CI instead of direct pushes to **`main`**.
- Boundary: this does not enable **`enforce_admins`**, does not change GitHub branch protection, and does not close R-001.
- Note: this is workflow rehearsal only; real external request remains **NOT AUTHORIZED** and live trading remains **NO-GO**.
#### 2026-05-31 — R-001 close decision after enforce-admins migration and post-enforcement PR verification
- R-001 §9 outcome: close
- Status (§6): **DONE**
- Decision: **NO-GO** for live trading
- Reason: **`enforce_admins.enabled = true`** is now verified on **`main`** branch protection; required checks **`check`** and **`checklist-curl-guardrails`** remain configured; **`required_status_checks.strict = true`** remains enabled; PR-only path was verified after enforcement through PR **#14**, which merged to **`main`** as **`92801fb`**.
- Close evidence: branch protection API verification, PR **#14** post-enforcement merge, and main **`local-box-baseline`** run **`26701688720`** completed **success**.
- Remaining blocker: runtime proof / real evidence collection is still not complete; closing R-001 does **not** authorize real external request or live trading.
- Note: R-001 is closed only for the branch-admin-bypass risk. **go-live remains NO-GO**, **real external request remains NOT AUTHORIZED**, and **live trading remains NO-GO**.
### WIP freeze roll (machine-checked — see `docs/RULES.md`)

When **`WIP freeze until`** is reached (current value lifts on **2026-05-15**), this review **must** explicitly record one of:

- **Roll forward:** edit **`docs/RULES.md`** to set
  - **`WIP freeze baseline:`** **`<new N>`** (usually current §4 `IN_PROGRESS` count from the `[info] §4 status:` line of the latest **`./scripts/check_go_live_rules.sh`** run)
  - **`WIP freeze until:`** **`<new YYYY-MM-DD>`**
- **Lift:** edit **`docs/RULES.md`** so today is past **`WIP freeze until`** (script will print `[info] WIP freeze OFF`); optionally adjust **WIP cap** default in the same file with reason.
- **Tighten cap permanently:** lower the **WIP cap** default in **`docs/RULES.md`** to the new agreed number; re-run **`./scripts/check_go_live_rules.sh`** to confirm `[result] PASS`.

Record the choice + reason here:

- Roll outcome (`ROLL_FORWARD | LIFT | TIGHTEN_CAP`):
- New baseline / until / cap:
- Reason:
- §4 snapshot at decision time (paste `[info] §4 status:` line):

---

## 10) Launch Week Run Sheet (T-7 to T+1)

- [ ] **T-7 to T-5:** freeze feature scope, finalize owner matrix, confirm rollout window
- [ ] **T-4 to T-3:** rerun deployment + rollback drill in stage
- [ ] **T-2:** verify alerts, on-call roster, escalation contacts
- [ ] **T-1:** final go/no-go review and signoff
- [ ] **T (launch):** canary rollout + watch SLO/alerts for agreed window
- [ ] **T+1:** post-launch review, open follow-up actions, close launch ticket

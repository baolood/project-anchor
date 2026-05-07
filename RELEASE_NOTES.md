# Release notes (template)

Fill in for each tagged release. Keep examples **portable** (use `/path/to/project-anchor`, not a developer home directory).

---

## Version <!-- e.g. 0.1.0 -->

**Date:** <!-- YYYY-MM-DD -->

### Highlights

- <!-- one or two bullets for readers skimming -->

### Added

- <!-- ... -->

### Changed

- <!-- ... -->

### Fixed

- <!-- ... -->

### Ops / migration

- <!-- e.g. new env vars, SQLite path (`LOCAL_BOX_DB_PATH`), compose changes; or “None” -->

### Submodule / subtree pointers

- **anchor-console:** <!-- submodule SHA or “unchanged” -->
- **anchor-backend:** <!-- note if subtree import was refreshed -->

### Upgrade notes

```bash
cd /path/to/project-anchor
git pull
python3 -m pip install -r requirements.txt
```

<!-- Add breaking changes or manual steps above the default pull/install block if needed. -->

---

## Version hardening-wave-2026-05-05

**Date:** 2026-05-05

### Highlights

- Completed repo-wide script hardening for portability and curl timeout safety.
- Added automated checklist curl guardrail scanner and wired it into CI baseline checks.

### Added

- `scripts/check_checklist_curl_guardrails.sh` to detect checklist `curl` timeout regressions.
- Dedicated CI job `checklist-curl-guardrails` in `.github/workflows/local-box-baseline.yml`.
- Runbook guardrail section for script strict mode, portable `ROOT`, and timeout patterns.

### Changed

- Standardized shell script strict mode and executable bits across tracked scripts.
- Standardized `curl` timeout usage across checklist/e2e scripts (`--connect-timeout 5 --max-time 20`).
- Updated CI/docs wording so guardrail failures are easier to triage locally.

### Fixed

- Removed/avoided machine-specific paths in script and docs workflows.
- Hardened flaky network call behavior to avoid silent hangs in long checklist runs.

### Ops / migration

- No runtime migration required.
- Maintainers should run before merge:
  - `./scripts/check_checklist_curl_guardrails.sh`
  - `./scripts/check_local_box_baseline.sh`

### Submodule / subtree pointers

- **anchor-console:** unchanged in this hardening wave
- **anchor-backend:** unchanged in this hardening wave (no subtree refresh in this batch)

### Upgrade notes

```bash
cd /path/to/project-anchor
git pull
python3 -m pip install -r requirements.txt
./scripts/check_checklist_curl_guardrails.sh
./scripts/check_local_box_baseline.sh
```

---

## Version go-live-tooling-2026-05-06

**Date:** 2026-05-06

### Highlights

- Executable go-live board, daily status reporter, and evidence layout under `artifacts/go-live/`.
- CI and parent baseline now guard the reporter and the tracked `artifacts/go-live/README.md` pointer.

### Added

- `docs/GO_LIVE_CHECKLIST.md` as the execution checklist; `scripts/go_live_status_report.sh` for standup metrics.
- `artifacts/go-live/README.md` (tracked); `artifacts/go-live/*.out` gitignored for daily snapshots.
- CI smoke step: `go_live_status_report.sh` in `.github/workflows/local-box-baseline.yml`.

### Changed

- `scripts/check_local_box_baseline.sh` requires `docs/GO_LIVE_CHECKLIST.md` and `artifacts/go-live/README.md`.
- Docs (`README.md`, `RUNBOOK.md`, `PR_DESCRIPTION.md`) aligned with CI job order and verifier commands.
- `scripts/go_live_status_report.sh` ensures parent directories exist before writing `--out` (standup path convenience).
- `local-box-baseline` workflow supports **`workflow_dispatch`** (GitHub **Actions** → **Run workflow**).
- `local-box-baseline` sets explicit **`permissions: contents: read`** for the token (least privilege).
- `local-box-baseline` jobs set **`timeout-minutes`** caps (curl guardrail `15`, check `30`) to shed stuck runs.
- Cross-links for CI timeouts surfaced in **`docs/GO_LIVE_CHECKLIST.md`** §1, **`PR_DESCRIPTION.md`** (hardening block), **`check_local_box_ci_runs.sh --help`**, **`artifacts/go-live/README.md`**, and **`go_live_status_report.sh --help`**.
- **`check_local_box_baseline.sh`** supports **`--help`**; **`local-box-baseline`** sets **`defaults.run.shell: bash`** for `run` steps.
- **`local-box-baseline`:** `actions/checkout` uses **`persist-credentials: false`**; job **`check`** sets job-level **`PYTHONPATH=.`** for Python smokes (removes duplicated step `env`). **`README.md`** (CI) + **`RUNBOOK.md`** (Parent repo CI) summarize these choices.
- **`local-box-baseline`:** **`actions/setup-python`** enables **pip** caching (`cache: pip`) with **`requirements.txt`** + **`requirements.in`** in **`cache-dependency-path`** so lock/in constraint changes refresh the cache key.
- **`README.md`:** workflow status badge for **`local-box-baseline`** (default branch).
- **`check_local_box_ci_runs.sh`:** adds **`--failed-only`** to isolate completed non-success, non-cancelled runs during triage; **`--failed-only`** cannot be combined with **`--cancelled-only`**.
- **`check_local_box_ci_runs.sh`:** adds **`--fail-on-failed`** for non-zero gating when filtered output contains completed failures.
- **`check_local_box_ci_runs.sh`:** adds alias **`--fail-on-non-success`** for readability (same behavior as **`--fail-on-failed`**).
- **`check_local_box_ci_runs.sh`:** adds **`--fail-on-incomplete`** to fail when filtered runs are still queued/in_progress (status != completed).
- **`check_local_box_ci_runs.sh`:** adds alias **`--fail-on-non-completed`** (same behavior as **`--fail-on-incomplete`**).
- **`check_local_box_ci_runs.sh`:** adds **`--gate-strict`** convenience preset (`--latest-only --fail-on-cancelled --fail-on-failed --fail-on-incomplete`).
- **`check_local_box_ci_runs.sh`:** `--gate-strict` now rejects `--cancelled-only` / `--canceled-only` / `--failed-only` combinations to prevent conflicting filters.
- **`check_local_box_ci_runs.sh`:** `--gate-strict` now also requires `--branch <name>` to avoid cross-branch ambiguity in strict gates.
- **`check_local_box_ci_runs.sh`:** `--gate-strict` now includes `--fail-on-cancelled` and `--fail-on-empty` so strict gates fail on cancelled latest runs or empty filtered output.
- **`check_local_box_ci_runs.sh`:** adds alias **`--strict`** (same behavior as **`--gate-strict`**).
- **`check_local_box_ci_runs.sh`:** strict-mode error messages now mention both spellings (`--gate-strict` / `--strict`) for clarity.
- **`check_local_box_ci_runs.sh`:** non-quiet `--gate-strict` prints the expanded preset flags for operator visibility.
- **`check_local_box_ci_runs.sh`:** option parsing now fails fast with explicit messages when `--workflow`, `--limit`, or `--branch` are provided without a value.
- **`go_live_status_report.sh`:** option parsing now fails fast with an explicit message when `--out` is provided without a path.
- **`check_checklist_curl_guardrails.sh`:** `--changed-only` now tolerates non-zero git probe commands (verbose mode logs skipped sources) instead of crashing with a Python traceback.
- **`check_local_box_ci_runs.sh`:** wraps `gh run list` failures with a stable `CI_RUNS_CHECK FAIL` message to improve operator triage context.
- **`check_local_box_ci_runs.sh`:** now rejects `--summary --json` as an explicit invalid combination (previously summary was silently skipped under JSON mode).
- **`check_local_box_ci_runs.sh`:** `--help` and docs now explicitly call out `--summary` / `--json` mutual exclusion for faster operator feedback.
- **`check_local_box_ci_runs.sh`:** cancelled-only vs failed-only mutual-exclusion error text now mentions both spellings (`--cancelled-only` / `--canceled-only`).
- **`check_local_box_ci_runs.sh`:** `--json` now implies quiet text mode so stdout remains pure JSON without human-readable banners/tips.
- **`check_local_box_ci_runs.sh`:** JSON row parsing now uses a bounded split so tab characters inside workflow titles do not corrupt structured fields.
- **Docs (`CONTRIBUTING.md`):** adds `--summary`/`--json` examples and clarifies their mutual exclusion plus JSON quiet-mode behavior.
- **Docs (`docs/GO_LIVE_CHECKLIST.md`, `PR_DESCRIPTION.md`):** aligns CI triage notes with `--summary`/`--json` mutual exclusion and JSON quiet-mode expectations.
- **`go_live_status_report.sh`:** now fails fast with a clear message when `--out` points to a directory instead of a file path.
- **`go_live_status_report.sh --help`:** now documents that `--out` must be a file path (directory targets are rejected).
- **`go_live_status_report.sh`:** now also rejects trailing-slash `--out` paths as directory-like targets with an explicit fail-fast message.
- **Docs (`README.md`, `RUNBOOK.md`):** now mirror the `--out` file-path-only constraint for `go_live_status_report.sh`.
- **Docs (`artifacts/go-live/README.md`, `CONTRIBUTING.md`, `docs/GO_LIVE_CHECKLIST.md` §7):** repeat the same `--out` file-path-only rule for contributors using the evidence layout.
- **`PR_DESCRIPTION.md`:** hardening-wave **Go-live tooling** bullet now repeats the **`go_live_status_report.sh --out`** file-path-only constraint.
- **`README.md`:** **Quick local checks** block includes an optional `--out` example with the same file-path-only reminder.
- **`CONTRIBUTING.md`**, **`PR_DESCRIPTION.md`:** **How to verify**, **Recommended verifier commands**, and local repro blocks mirror the same optional `--out` comment.
- **`RUNBOOK.md`:** Script maintenance guardrails baseline block includes the same optional `--out` comment.
- **`local-box-baseline.yml`:** comment above the go-live reporter smoke step documents that CI uses stdout only and local `--out` must be a file path.
- **`README.md`:** CI step list item for **`go_live_status_report.sh`** echoes the same stdout vs local **`--out`** distinction.
- **`RUNBOOK.md`:** Parent repo CI summary adds the same **`go_live_status_report.sh`** stdout vs local **`--out`** note.
- **`artifacts/go-live/README.md`**, **`CONTRIBUTING.md`:** CI vs local **`go_live_status_report.sh`** behavior (stdout-only in Actions; **`--out`** file path locally) spelled out for snapshot writers.
- **`docs/GO_LIVE_CHECKLIST.md`:** §1 **CI coupling** and §7 standup bullets contrast CI stdout-only runs vs local **`--out`** evidence; **`PR_DESCRIPTION.md`** hardening summary matches.
- **`PR_DESCRIPTION.md`:** Go-live checklist item now repeats the same CI stdout-only vs local **`--out`** file-path distinction for PR authors.
- **`docs/RULES.md`:** operational rules **SSOT** for **`go_live_status_report.sh`** (**stdout-only** in CI vs **`--out`** file path locally).
- **`scripts/check_go_live_rules.sh`:** validates anchors in **`docs/RULES.md`** only (CI + local hooks share one contract).
- **`local-box-baseline.yml`:** job **`check`** runs **`./scripts/check_go_live_rules.sh`** between baseline and the reporter smoke, so the SSOT anchors are enforced as a CI gate (must pass to merge).
- **`.githooks/pre-commit`** + **`scripts/install_git_hooks.sh`:** optional **`git commit`** gate (baseline + go-live rules) via **`git config core.hooksPath`**.
- **`AGENTS.md`:** concise defaults for automation agents (repro order + SSOT pointer).
- **`docs/GITHUB_BRANCH_PROTECTION.md`:** repo-admin checklist to require **`local-box-baseline`** status checks on **`main`**.
- **`README.md` / `CONTRIBUTING.md` / `PR_DESCRIPTION.md` / `RUNBOOK.md` / `docs/GO_LIVE_CHECKLIST.md` / `artifacts/go-live/README.md`:** summaries link **`docs/RULES.md`**; verifier blocks include **`./scripts/check_go_live_rules.sh`** where they mirror CI.
- **`CONTRIBUTING.md`:** new **First-time setup** block (`brew install gh` → `gh auth login` → `./scripts/install_git_hooks.sh`) for fresh clones.
- **`docs/GO_LIVE_CHECKLIST.md` §0:** milestones M0/M1 now have concrete **target dates** (M0 2026-05-29, M1 2026-07-10), testable acceptance lists tied to §4 sections, and an explicit **cutoff rule** (NO-GO + risk register row + reschedule cadence).
- **`docs/GO_LIVE_CHECKLIST.md` §5:** hard gates expanded into IDs **G1–G6** with verifier role, evidence type, and linked-plan anchors per gate (no change in `- [ ]` count, so the reporter denominator stays stable).
- **`docs/GO_LIVE_CHECKLIST.md` §4 Week 1:** “Define go-live gates” → `DONE` (evidence: §5 **G1–G6** + commit **`fd7d4d8`**); “Freeze release branch policy” → `IN_PROGRESS` with evidence **`docs/RELEASE_BRANCH_POLICY.md`**.
- **`docs/GO_LIVE_CHECKLIST.md` §2:** interim owner matrix — all roles assigned to **`baolood`** until staffing splits.
- **`docs/GO_LIVE_CHECKLIST.md` §6:** **R-001** opened — **`main`** branch protection not yet enforced (ETA **2026-05-14**).
- **`docs/RELEASE_BRANCH_POLICY.md`:** draft policy for **`main`**, PR discipline, tags/rollback, submodule pointer bumps.
- **`CONTRIBUTING.md`:** branch-protection section links **`docs/RELEASE_BRANCH_POLICY.md`** and **`docs/GO_LIVE_CHECKLIST.md`** §6 **R-001** until **`main`** protection is GREEN.
- **`docs/GITHUB_BRANCH_PROTECTION.md`:** keeps **Web UI** steps; adds cross-link to **`docs/RELEASE_BRANCH_POLICY.md`** after protection is enabled.
- **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`:** Week 1 parity working template (runtime, deps, SQLite defaults, guardrail paths, intentional deltas).
- **`docs/GO_LIVE_CHECKLIST.md` §4 Week 1:** “Prod-like environment parity check” → `IN_PROGRESS` (owner **baolood**, evidence **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`**).
- **`docs/GO_LIVE_CHECKLIST.md` §6 / R-001:** mitigation now notes **`gh auth login`** prerequisite for strict **`check_local_box_ci_runs.sh`** gates.
- **`CONTRIBUTING.md`:** Go-live execution artifacts list links **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`**.
- **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`:** §1–§4 prefilled with real maintainer data (`Darwin/arm64`, Python **3.8.10**, SQLite **3.35.5**, default `anchor.db` path, guardrail file presence); §5 lists known deltas; sign-off captured for **`baolood`** dated **2026-05-07** (stage column intentionally TBD).
- **`docs/GO_LIVE_CHECKLIST.md` §6:** **R-002** opened — Python version drift (local **3.8.10** vs CI **3.11**), owner **baolood**, ETA **2026-05-21**.
- **`docs/STAGE_DEPLOY_RUNBOOK.md`:** Week 2 one-command **stage deploy** draft (compose path from **`RUNBOOK.md`** Daily Mode + post-deploy smoke + duration table placeholders).
- **`docs/GO_LIVE_CHECKLIST.md` §4 Week 2:** “One-command deployment runbook validated” → `IN_PROGRESS` (owner **baolood**, evidence **`docs/STAGE_DEPLOY_RUNBOOK.md`**).
- **`CONTRIBUTING.md`:** Go-live artifacts list links **`docs/STAGE_DEPLOY_RUNBOOK.md`**.
- **`RUNBOOK.md`:** Daily Mode links the Week 2 stage deploy draft for discoverability.
- **`docs/ROLLBACK_DRILL_RUNBOOK.md`:** Week 2 **rollback drill** draft (preconditions, two rollback paths, drill log table, post-rollback smoke).
- **`docs/GO_LIVE_CHECKLIST.md` §4 Week 2:** “Rollback drill completed” → `IN_PROGRESS` (owner **baolood**, evidence **`docs/ROLLBACK_DRILL_RUNBOOK.md`**).
- **`docs/RELEASE_BRANCH_POLICY.md`:** **Tags and rollback** now points to the Week 2 drill runbook for the structured procedure.
- **`CONTRIBUTING.md`:** Go-live artifacts list links **`docs/ROLLBACK_DRILL_RUNBOOK.md`**.
- **`docs/ON_CALL_SOP.md`:** Week 2 **on-call SOP** draft (P0–P3 matrix, escalation ladder, first-response checklist, notification templates).
- **`docs/GO_LIVE_CHECKLIST.md` §4 Week 2:** “On-call SOP draft complete” → `IN_PROGRESS` (owner **baolood**, evidence **`docs/ON_CALL_SOP.md`**).
- **`CONTRIBUTING.md`:** Go-live artifacts list links **`docs/ON_CALL_SOP.md`**.
- **`docs/SERVICE_SLI_SLO.md`:** Week 3 **SLI/SLO** draft (service table, SLI candidates, placeholder SLO targets, review cadence).
- **`docs/GO_LIVE_CHECKLIST.md` §4 Week 3:** “Define service SLI/SLO” → `IN_PROGRESS` (owner **baolood**, evidence **`docs/SERVICE_SLI_SLO.md`**).
- **`CONTRIBUTING.md`:** Go-live artifacts list links **`docs/SERVICE_SLI_SLO.md`**.
- **`docs/ALERTING_ROUTING.md`:** Week 3 **alerting + routing** draft (severity routing matrix, alert rule candidates AL-AVAIL/LATENCY/ERRORS/WORKER/DEPLOY, required test before sign-off).
- **`docs/GO_LIVE_CHECKLIST.md` §4 Week 3:** “Alert rules + routing implemented” → `IN_PROGRESS` (owner **baolood**, evidence **`docs/ALERTING_ROUTING.md`**).
- **`CONTRIBUTING.md`:** Go-live artifacts list links **`docs/ALERTING_ROUTING.md`**.
- **`docs/SYNTHETIC_CHECKS.md`:** Week 3 **synthetic checks** draft (probe inventory, `curl` timeout policy, routing into alerts, local sanity command).
- **`docs/GO_LIVE_CHECKLIST.md` §4 Week 3:** “Synthetic checks for critical endpoints” → `IN_PROGRESS` (owner **baolood**, evidence **`docs/SYNTHETIC_CHECKS.md`**).
- **`CONTRIBUTING.md`:** Go-live artifacts list links **`docs/SYNTHETIC_CHECKS.md`**.
- **`check_checklist_curl_guardrails.sh`:** `--changed-only` now also handles missing `git` binaries gracefully (verbose mode prints skipped source details) instead of raising Python exceptions.
- **Docs:** add CI-friendly `--gate-strict --quiet` examples for scriptable exit-code checks.
- **`check_local_box_ci_runs.sh --help`:** now includes common command examples, including strict gate usage.
- **`check_local_box_ci_runs.sh`:** missing-`gh` error now prints a concrete install hint (macOS `brew install gh` + upstream URL).
- **`check_local_box_ci_runs.sh --help`:** examples now explicitly show `--fail-on-empty` and alias forms (`--fail-on-non-success`, `--fail-on-non-completed`).
- **`check_local_box_ci_runs.sh`:** adds **`--fail-on-empty`** to fail when filtered output has zero rows.
- **`check_local_box_ci_runs.sh`:** adds alias **`--fail-on-canceled`** (same behavior as **`--fail-on-cancelled`**).
- **`check_local_box_ci_runs.sh`:** adds alias **`--canceled-only`** (same behavior as **`--cancelled-only`**).
- **`check_local_box_ci_runs.sh`:** **`--branch`** forwards to **`gh run list --branch`**; **`--require-latest-success`** uses the first row returned (branch-scoped, newest-first).
- **Docs:** **`docs/GO_LIVE_CHECKLIST.md`** §1, **`PR_DESCRIPTION.md`**, and **`RUNBOOK.md`** updated for branch-scoped `gh` listing, **`--failed-only`** vs **`--cancelled-only`** mutual exclusion, and gate flags (**`--fail-on-failed`** / **`--fail-on-non-success`** / **`--fail-on-incomplete`**).
- **`.github/pull_request_template.md`:** default PR body stub pointing contributors to **`PR_DESCRIPTION.md`** (also required by **`check_local_box_baseline.sh`**).
- **Governance:** **`docs/GO_LIVE_CHECKLIST.md`** §1 and **`PR_DESCRIPTION.md`** checklist spell out how checklist path changes must stay aligned with **`check_local_box_baseline.sh`** and **`go_live_status_report.sh`**.
- **`local-box-baseline`:** job **`check`** sets **`PIP_NO_INPUT=1`** and **`PIP_DISABLE_PIP_VERSION_CHECK=1`** for **`pip`** steps; **pip upgrade** and **`requirements.txt` install** are separate Actions steps for clearer logs.

### Ops / migration

- No production runtime migration.
- Optional local standup habit: see `docs/GO_LIVE_CHECKLIST.md` §7.

### Upgrade notes

```bash
cd /path/to/project-anchor
git pull
./scripts/go_live_status_report.sh
./scripts/check_local_box_baseline.sh
./scripts/check_go_live_rules.sh
```

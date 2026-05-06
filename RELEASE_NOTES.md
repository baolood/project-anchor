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
- **`check_local_box_ci_runs.sh`:** adds **`--gate-strict`** convenience preset (`--latest-only --fail-on-failed --fail-on-incomplete`).
- **`check_local_box_ci_runs.sh`:** `--gate-strict` now rejects `--cancelled-only` / `--failed-only` combinations to prevent conflicting filters.
- **`check_local_box_ci_runs.sh`:** `--gate-strict` now also requires `--branch <name>` to avoid cross-branch ambiguity in strict gates.
- **`check_local_box_ci_runs.sh`:** adds **`--fail-on-empty`** to fail when filtered output has zero rows.
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
```

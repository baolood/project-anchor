# Contributing

This repo is a **parent/orchestration** repository. Most changes fall into one of these buckets:

- **Docs / operations** (`README.md`, `RUNBOOK.md`, `docs/`)
- **CI / guardrails** (`.github/workflows/local-box-baseline.yml`, `scripts/check_*`)
- **Parent Python package** (`local_box/` + repo-root `requirements.txt`)

## First-time setup (recommended)

After cloning, in the repo root:

```bash
brew install gh                  # macOS; pick the equivalent on your platform
gh auth login                    # one-time GitHub CLI auth (for ./scripts/check_local_box_ci_runs.sh)
./scripts/install_git_hooks.sh   # enable pre-commit guardrails (baseline + go-live rules)
```

## Developer workflow (quick)

```bash
cd /path/to/project-anchor
export PYTHONPATH=.
python3 -m pip install -r requirements.txt
```

## Git hooks (optional)

Install repo-managed hooks so **`git commit`** runs the same fast guardrails as CI expects (baseline + go-live rules):

```bash
./scripts/install_git_hooks.sh
```

Hooks live under **`.githooks/`** (not the default **`.git/hooks/`**). Remove with **`git config --unset core.hooksPath`** from the repo root if you need to disable them.

## CI and local reproduction

GitHub Actions workflow: **`.github/workflows/local-box-baseline.yml`** (two jobs).

Local repro (same order as CI job **check**):

```bash
./scripts/check_checklist_curl_guardrails.sh
./scripts/check_local_box_baseline.sh
./scripts/check_go_live_rules.sh
./scripts/go_live_status_report.sh
# Optional standup artifact (--out must be a file path, not a directory):
# ./scripts/go_live_status_report.sh --out artifacts/go-live/go_live_daily_status_$(date +%F).out
python3 -c "from local_box.audit import event_store; event_store.init_db(); print('LOCAL_BOX_SQLITE_SMOKE ok')"
```

Notes:
- **Operational rules (SSOT):** **`docs/RULES.md`** — canonical **CI vs local** wording for **`go_live_status_report.sh`**; enforced by **`./scripts/check_go_live_rules.sh`**.
- `./scripts/check_local_box_baseline.sh --help` explains what it validates (includes **`docs/RULES.md`**, **`docs/GO_LIVE_CHECKLIST.md`**).
- The workflow supports **`workflow_dispatch`** (manual run) via GitHub **Actions** → **local-box-baseline** → **Run workflow**.
- In CI, **`go_live_status_report.sh`** runs **stdout only** (parses the checklist; no file artifact). Locally, use **`--out`** for standup evidence (must be a **file** path — see **`./scripts/go_live_status_report.sh --help`**).
- In CI, job **`check`** sets **`PIP_NO_INPUT=1`** (and **`PIP_DISABLE_PIP_VERSION_CHECK=1`**) during **`pip install`** — optional for local scripts but matches CI behavior.

### Inspect workflow runs (GitHub CLI)

Requires `gh` + `gh auth login`.

**Note:** `--branch` is forwarded to `gh run list --branch` so the newest runs for that branch are not “hidden” behind other branches in the global limit window.

```bash
./scripts/check_local_box_ci_runs.sh --branch main --limit 20
./scripts/check_local_box_ci_runs.sh --branch main --failed-only --limit 30
./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-failed  # alias: --fail-on-non-success
./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-incomplete  # alias: --fail-on-non-completed
./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-empty
./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-canceled
./scripts/check_local_box_ci_runs.sh --branch main --latest-only --summary
./scripts/check_local_box_ci_runs.sh --branch main --latest-only --json
./scripts/check_local_box_ci_runs.sh --branch main --gate-strict
./scripts/check_local_box_ci_runs.sh --branch main --gate-strict --quiet
```

Do not combine **`--cancelled-only`** with **`--failed-only`** (the script exits with an error). Also, **`--gate-strict` (alias: `--strict`)** requires **`--branch`** and cannot be combined with those two filter flags.
`--summary` and `--json` are mutually exclusive, and `--json` implies quiet text mode so stdout stays machine-readable.

## GitHub branch protection (repo admins)

To require **`local-box-baseline`** checks before merging to **`main`**, follow **`docs/GITHUB_BRANCH_PROTECTION.md`** (web UI is the most reliable path).

Branching, tags, and rollback expectations for **`main`** live in **`docs/RELEASE_BRANCH_POLICY.md`** (draft until protection is GREEN — see **`docs/GO_LIVE_CHECKLIST.md`** §6 **R-001**).

## Pull requests

GitHub opens **`.github/pull_request_template.md`** when you create a PR. The canonical checklist and wording live in **`PR_DESCRIPTION.md`** at the repo root — copy from there into the PR body. **`./scripts/check_local_box_baseline.sh`** treats the stub file as required (do not delete it without updating the baseline list).

## Go-live execution artifacts

- Execution board: **`docs/GO_LIVE_CHECKLIST.md`**
- **Operational rules (SSOT):** **`docs/RULES.md`**
- **Environment parity (Week 1):** **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`**
- **Stage deploy runbook (Week 2, draft):** **`docs/STAGE_DEPLOY_RUNBOOK.md`**
- **Rollback drill runbook (Week 2, draft):** **`docs/ROLLBACK_DRILL_RUNBOOK.md`**
- **On-call SOP (Week 2, draft):** **`docs/ON_CALL_SOP.md`**
- **SLI / SLO draft (Week 3):** **`docs/SERVICE_SLI_SLO.md`**
- **Alerting + routing draft (Week 3):** **`docs/ALERTING_ROUTING.md`**
- **Synthetic checks draft (Week 3):** **`docs/SYNTHETIC_CHECKS.md`**
- **Backup + recovery strategy (Week 4, draft):** **`docs/BACKUP_AND_RECOVERY.md`**
- **Restore drill runbook (Week 4, draft):** **`docs/RESTORE_DRILL_RUNBOOK.md`**
- **Migration rollback runbook (Week 4, draft):** **`docs/MIGRATION_ROLLBACK_RUNBOOK.md`**
- **Secrets + rotation (Week 5-6, draft):** **`docs/SECRETS_AND_ROTATION.md`**
- **Permission audit (Week 5-6, draft):** **`docs/PERMISSION_AUDIT.md`**
- **Capacity + stress test (Week 5-6, draft):** **`docs/CAPACITY_TEST_PLAN.md`**
- Daily snapshot tool: **`./scripts/go_live_status_report.sh --out artifacts/go-live/go_live_daily_status_$(date +%F).out`**
- **`--out`** must target a file path, not a directory (see **`./scripts/go_live_status_report.sh --help`**).
- `artifacts/go-live/*.out` is gitignored; the tracked pointer is `artifacts/go-live/README.md`.

## Style / safety guardrails

- **Portable paths:** use repo-relative paths and placeholders like `/path/to/project-anchor` (avoid `/Users/...`).
- **Bash strict mode:** prefer `#!/usr/bin/env bash` + `set -euo pipefail`.
- **Checklist networking:** checklist scripts must keep `curl` timeouts (`--connect-timeout` and `--max-time`), enforced by `check_checklist_curl_guardrails.sh`.


# Contributing

This repo is a **parent/orchestration** repository. Most changes fall into one of these buckets:

- **Docs / operations** (`README.md`, `RUNBOOK.md`, `docs/`)
- **CI / guardrails** (`.github/workflows/local-box-baseline.yml`, `scripts/check_*`)
- **Parent Python package** (`local_box/` + repo-root `requirements.txt`)

## Developer workflow (quick)

```bash
cd /path/to/project-anchor
export PYTHONPATH=.
python3 -m pip install -r requirements.txt
```

## CI and local reproduction

GitHub Actions workflow: **`.github/workflows/local-box-baseline.yml`** (two jobs).

Local repro (same order as CI job **check**):

```bash
./scripts/check_checklist_curl_guardrails.sh
./scripts/check_local_box_baseline.sh
./scripts/go_live_status_report.sh
python3 -c "from local_box.audit import event_store; event_store.init_db(); print('LOCAL_BOX_SQLITE_SMOKE ok')"
```

Notes:
- `./scripts/check_local_box_baseline.sh --help` explains what it validates (includes **`docs/GO_LIVE_CHECKLIST.md`**).
- The workflow supports **`workflow_dispatch`** (manual run) via GitHub **Actions** → **local-box-baseline** → **Run workflow**.
- In CI, job **`check`** sets **`PIP_NO_INPUT=1`** (and **`PIP_DISABLE_PIP_VERSION_CHECK=1`**) during **`pip install`** — optional for local scripts but matches CI behavior.

### Inspect workflow runs (GitHub CLI)

Requires `gh` + `gh auth login`.

**Note:** `--branch` is forwarded to `gh run list --branch` so the newest runs for that branch are not “hidden” behind other branches in the global limit window.

```bash
./scripts/check_local_box_ci_runs.sh --branch main --limit 20
./scripts/check_local_box_ci_runs.sh --branch main --failed-only --limit 30
./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-failed  # alias: --fail-on-non-success
./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-incomplete
./scripts/check_local_box_ci_runs.sh --branch main --latest-only --fail-on-empty
./scripts/check_local_box_ci_runs.sh --branch main --gate-strict
```

Do not combine **`--cancelled-only`** with **`--failed-only`** (the script exits with an error). Also, **`--gate-strict`** requires **`--branch`** and cannot be combined with those two filter flags.

## Pull requests

GitHub opens **`.github/pull_request_template.md`** when you create a PR. The canonical checklist and wording live in **`PR_DESCRIPTION.md`** at the repo root — copy from there into the PR body. **`./scripts/check_local_box_baseline.sh`** treats the stub file as required (do not delete it without updating the baseline list).

## Go-live execution artifacts

- Execution board: **`docs/GO_LIVE_CHECKLIST.md`**
- Daily snapshot tool: **`./scripts/go_live_status_report.sh --out artifacts/go-live/go_live_daily_status_$(date +%F).out`**
- `artifacts/go-live/*.out` is gitignored; the tracked pointer is `artifacts/go-live/README.md`.

## Style / safety guardrails

- **Portable paths:** use repo-relative paths and placeholders like `/path/to/project-anchor` (avoid `/Users/...`).
- **Bash strict mode:** prefer `#!/usr/bin/env bash` + `set -euo pipefail`.
- **Checklist networking:** checklist scripts must keep `curl` timeouts (`--connect-timeout` and `--max-time`), enforced by `check_checklist_curl_guardrails.sh`.


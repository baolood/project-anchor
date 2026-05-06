# Project Anchor — Risk Core Runbook

Throughout this file, **`/path/to/project-anchor`** means your local clone of the repository (replace with the real directory).

For launch planning and owner tracking, use **`docs/GO_LIVE_CHECKLIST.md`** as the execution board.
Daily progress snapshot:
```bash
./scripts/go_live_status_report.sh
./scripts/go_live_status_report.sh --out artifacts/go-live/go_live_daily_status_$(date +%F).out
# mkdir -p artifacts/go-live   # optional: --out creates parent dirs if missing
# Ad-hoc only: ./scripts/go_live_status_report.sh --out /tmp/go_live_daily_status.out
```
(`artifacts/go-live/*.out` is gitignored; see `artifacts/go-live/README.md` and `docs/GO_LIVE_CHECKLIST.md` §7.)

## Parent repo CI (GitHub Actions)

- Workflow: **`.github/workflows/local-box-baseline.yml`** (`local-box-baseline`). Also runnable on demand (**Actions** → **local-box-baseline** → **Run workflow**) via **`workflow_dispatch`**. Inline `run:` steps use **`defaults.run.shell: bash`**.
- **`actions/checkout`** sets **`persist-credentials: false`** (read-only clone only). Job **`check`** sets **`PYTHONPATH=.`** once for the Python smoke steps.
- **`actions/setup-python`** uses **`cache: pip`** with **`cache-dependency-path`** covering **`requirements.txt`** and **`requirements.in`** so constraint edits invalidate the pip cache cleanly.
- Job **`check`** exports **`PIP_NO_INPUT=1`** and **`PIP_DISABLE_PIP_VERSION_CHECK=1`** during **`pip`** steps (CI-safe, non-interactive). The workflow uses separate steps for **pip upgrade** vs **`requirements.txt` install** so failures are easier to read in Actions.
- Two jobs: **`checklist-curl-guardrails`** (checklist `curl` policy) and **`check`** (deps, `check_local_box_baseline.sh`, `go_live_status_report.sh`, SQLite/import smokes).
- Full job order, failure triage, and `gh` examples: root **`README.md`** → section **CI** (this section is the short ops summary).
- Quick fail triage helper: `./scripts/check_local_box_ci_runs.sh --branch <your-branch> --failed-only` (**`--branch`** is passed through to **`gh`**; scope per-branch before **`--limit`** truncates the list). For pipeline gating, add `--latest-only --fail-on-failed` (alias: `--fail-on-non-success`). Add `--fail-on-incomplete` (alias: `--fail-on-non-completed`) when gates must fail on queued/in-progress runs, and `--fail-on-empty` when missing rows should fail fast. Shortcut: `--gate-strict` (= `--latest-only --fail-on-failed --fail-on-incomplete --fail-on-empty`, requires `--branch`), and do not combine it with `--cancelled-only` / `--failed-only`. For automation, prefer `--gate-strict --quiet`.
- Each job declares **`timeout-minutes`** in the workflow YAML (see **`.github/workflows/local-box-baseline.yml`**).

## Daily Mode (default)

### Start (backend + worker)

With `docker-compose.override.yml` present, worker picks up daily defaults; no manual env needed:
```bash
cd /path/to/project-anchor/anchor-backend
docker compose up -d --build
docker compose stop worker 2>/dev/null || true
sleep 2
docker compose up -d worker
```

Without override, use explicit env (see Extreme Mode for override bypass):
```bash
CAPITAL_USD=1000 MAX_SINGLE_TRADE_RISK_PCT=0.5 MAX_NET_EXPOSURE_PCT=30 MAX_LEVERAGE=5 MAX_DAILY_DRAWDOWN_PCT=3 \
RISK_HARD_LIMITS_DISABLE=0 RISK_EXPOSURE_ATOMIC=1 docker compose up -d worker
```

## Extreme Mode (stress test)

### Enter extreme
```bash
cd /path/to/project-anchor
BASE="http://127.0.0.1:8000" CAPITAL_USD=1000 ./scripts/extreme_mode_run.sh
```

### Or step-by-step
```bash
cd /path/to/project-anchor/anchor-backend
docker compose stop worker
sleep 2
CAPITAL_USD=1000 MAX_SINGLE_TRADE_RISK_PCT=100 MAX_NET_EXPOSURE_PCT=30 \
RISK_HARD_LIMITS_DISABLE=0 RISK_EXPOSURE_ATOMIC=1 \
docker compose up -d worker
```

## Parent repo — `local_box` (Python + SQLite)

For the **parent repository** `local_box` audit stack (not Docker `anchor-backend`):

1. **Install Python deps** (from repo root):

   ```bash
   cd /path/to/project-anchor
   python3 -m pip install -r requirements.txt
   ```

2. **SQLite path** (`local_box/audit/event_store.py`):

   - **Default:** `<repo-root>/anchor.db` (resolved from `local_box/audit/event_store.py`, not machine-specific).
   - **Override:** set **`LOCAL_BOX_DB_PATH`** to an absolute path or `~`-expanded path if the default location is not writable.

   ```bash
   export LOCAL_BOX_DB_PATH="$PWD/tmp/local_box_ci.db"
   mkdir -p tmp
   ```

3. **Import smoke** (optional, after `pip install`):

   ```bash
   export PYTHONPATH=.
   python3 -c "from local_box.audit import event_store; event_store.init_db(); print('ok', event_store.DB_PATH)"
   python3 -c "import local_box.runner; print('runner import ok')"
   ```

4. **CI:** workflow **`.github/workflows/local-box-baseline.yml`** runs `pip install -r requirements.txt`, `./scripts/check_local_box_baseline.sh` (includes checklist curl guardrail scan), then SQLite **`init_db()`** smoke, **`import local_box.runner`**, and **`import local_box.control.server`** (Flask app). Concurrent runs on the same ref are cancelled via workflow **`concurrency`**.
   - Expected signal under frequent pushes: older runs on the same ref can appear **Cancelled**; this is normal.
   - Validation rule: check the **latest run on the ref** for final PASS/FAIL.
   - Optional helper (requires GitHub CLI auth):
     ```bash
     ./scripts/check_local_box_ci_runs.sh
     ./scripts/check_local_box_ci_runs.sh --branch main --limit 20
     ./scripts/check_local_box_ci_runs.sh --workflow local-box-baseline.yml --branch <your-branch>
     ./scripts/check_local_box_ci_runs.sh --branch <your-branch> --cancelled-only
     ./scripts/check_local_box_ci_runs.sh --latest-only
     ./scripts/check_local_box_ci_runs.sh --branch <your-branch> --latest-only --summary
     ./scripts/check_local_box_ci_runs.sh --branch <your-branch> --require-latest-success
     ./scripts/check_local_box_ci_runs.sh --branch <your-branch> --require-latest-success --quiet
     ./scripts/check_local_box_ci_runs.sh --branch <your-branch> --latest-only --json
     ./scripts/check_local_box_ci_runs.sh --branch <your-branch> --latest-only --fail-on-cancelled
     ```

5. **Local parity with CI** (from repo root, after `pip install -r requirements.txt`):

   ```bash
   export PYTHONPATH=.
   python3 -c "import local_box.control.server as c; print('control', c.app.name)"
   ```

## Script maintenance guardrails

When adding or updating shell automation under `scripts/` (and checklist scripts), keep these defaults so local runs and CI behave the same:

1. **Strict mode first**
   - Use `#!/usr/bin/env bash` and `set -euo pipefail`.
   - Prefer explicit non-fatal handling (`|| true`) only where intentional.

2. **Portable repository paths**
   - Resolve repository root from script location, not machine-specific paths:
     ```bash
     ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
     ```
   - Use quoted path joins, e.g. `cd "$ROOT/anchor-backend"`.

3. **Network call safety (`curl`)**
   - For HTTP calls in E2E/checklist scripts, use timeout guards:
     - `--connect-timeout 5`
     - `--max-time 20`
   - Recommended pattern:
     ```bash
     CURL_FLAGS=( -sS --connect-timeout 5 --max-time 20 --noproxy '*' )
     curl "${CURL_FLAGS[@]}" "$URL"
     ```
   - Keep existing auth/header option arrays; merge timeout flags rather than replacing behavior.

4. **Validation before commit**
   - Syntax-check changed scripts:
     ```bash
     bash -n scripts/your_script.sh
     ```
   - Run checklist curl timeout guardrail scan:
     ```bash
     ./scripts/check_checklist_curl_guardrails.sh
     ```
   - Optional modes for local developer loops:
     ```bash
     ./scripts/check_checklist_curl_guardrails.sh --verbose
     ./scripts/check_checklist_curl_guardrails.sh --changed-only
     ```
   - For parent baseline safety (matches CI `check` job order), run:
     ```bash
     ./scripts/check_local_box_baseline.sh
     ./scripts/go_live_status_report.sh
     python3 -c "from local_box.audit import event_store; event_store.init_db(); print('LOCAL_BOX_SQLITE_SMOKE ok')"
     ```
   - Baseline also requires **`docs/GO_LIVE_CHECKLIST.md`** (go-live board / reporter input) and **`.github/pull_request_template.md`** (PR body stub); renaming or removing either file needs a matching edit to **`scripts/check_local_box_baseline.sh`**.

## Verify

### Full E2E (default: EXTREME skipped)
```bash
cd /path/to/project-anchor
./scripts/release_up_and_verify.sh
```

### With EXTREME gate
```bash
EXTREME_MODE_E2E=1 ./scripts/release_up_and_verify.sh
```

### Risk hard limits only
```bash
./scripts/checklist_risk_hard_limits_e2e.sh
```

## Reset

### Reset exposure + clean pending
```bash
curl -s -X POST http://127.0.0.1:8000/ops/dev/reset-pending-domain-commands
cd /path/to/project-anchor/anchor-backend
docker compose exec -T postgres psql -U anchor -d anchor -c \
  "UPDATE risk_state SET current_exposure_usd=0, updated_at=NOW() WHERE id=1;"
```

## Tag Release (固化 daily env + 验证 + 打 tag)

```bash
cd /path/to/project-anchor
./scripts/risk_core_tag_release.sh
```

生成 `docker-compose.override.yml`，执行 release 验证，打 `risk-core-v2` 并推送。

## Evidence (paths)

- `/tmp/anchor_risk_core_tag_head.out`
- `/tmp/anchor_e2e_release_after_daily_default_env.out`
- `/tmp/anchor_e2e_release_up_and_verify_last.out`
- `/tmp/anchor_e2e_verify_all_release.out`
- `/tmp/anchor_e2e_index_last.out`
- `/tmp/anchor_e2e_checklist_extreme_mode_e2e_last.out`
- `/tmp/anchor_extreme_outcome_last.out`
- `/tmp/anchor_extreme_risk_state_last.json`
- `/tmp/anchor_extreme_daily_smoke_last.out`
- `/tmp/anchor_e2e_checklist_risk_hard_limits_e2e_last.out`

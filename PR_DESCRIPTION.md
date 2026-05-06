# Pull request description (template)

Copy this file into the GitHub PR body and replace the placeholders. GitHub also opens **`.github/pull_request_template.md`** as a short stub that points here — keep both in sync conceptually (canonical wording lives in this file). Use **repo-relative** paths and portable examples (for example `cd /path/to/project-anchor`), not machine-specific absolute paths.

## Summary

- **What:** <!-- one sentence -->
- **Why:** <!-- problem or ticket reference -->

## Scope

- **Areas touched:** <!-- e.g. local_box, scripts, anchor-backend subtree, anchor-console submodule pointer -->
- **Out of scope:** <!-- explicit non-goals -->

## How to verify

```bash
cd /path/to/project-anchor
export PYTHONPATH=.
./scripts/check_local_box_baseline.sh
./scripts/go_live_status_report.sh
python3 -c "from local_box.audit import event_store; event_store.init_db(); print('LOCAL_BOX_SQLITE_SMOKE ok')"
```

<!-- If you change checklist `curl` usage or `checklist_*.sh`, also run `./scripts/check_checklist_curl_guardrails.sh`. -->
<!-- Add service-specific steps (docker compose, UI) if relevant. -->

## Risk / rollout

- **User-visible behavior:** <!-- none / describe -->
- **Migrations / data:** <!-- N/A or describe -->
- **Submodule / subtree:** <!-- N/A or SHA bump noted -->

## Checklist

- [ ] **CI:** `local-box-baseline` (or equivalent) considered for this change (on-demand re-run: GitHub **Actions** → **local-box-baseline** → **Run workflow** / `workflow_dispatch`)
- [ ] **Go-live:** if you change `artifacts/go-live/`, `docs/GO_LIVE_CHECKLIST.md`, or `scripts/go_live_status_report.sh`, run `./scripts/go_live_status_report.sh` and ensure `./scripts/check_local_box_baseline.sh` still passes; **renaming the checklist file** requires updating **`check_local_box_baseline.sh`** (`REQUIRED_PATHS`), **`go_live_status_report.sh`** (default checklist path / `CHECKLIST_FILE`), and docs/CI references
- [ ] **GitHub PR stub:** if you rename/remove **`.github/pull_request_template.md`**, update **`scripts/check_local_box_baseline.sh`** (`REQUIRED_PATHS`) and docs links
- [ ] **Docs:** `README.md` / `RUNBOOK.md` / ADRs updated if behavior or ops changed
- [ ] **Paths:** examples and scripts avoid machine-specific absolute paths (use repo-relative paths or placeholders like `/path/to/project-anchor`)
- [ ] **Secrets:** no credentials committed

---

## Optional Release Summary Block (copy when needed)

Use this section when the PR is part of a hardening/governance wave and you want a release-note-friendly summary directly in the PR body.

### Hardening wave summary

- **Portable paths:** scripts/docs avoid machine-specific absolute paths.
- **Script safety:** strict bash mode and executable-bit normalization applied.
- **Checklist networking:** `curl` timeout guardrails standardized (`--connect-timeout 5 --max-time 20`).
- **CI guardrail:** dedicated `checklist-curl-guardrails` job + baseline integration + `workflow_dispatch` + per-job `timeout-minutes` caps; checkout **`persist-credentials: false`**; job **`check`** uses job-level **`PYTHONPATH=.`** for smoke steps; **`setup-python`** **pip** cache on **`requirements.txt`** / **`requirements.in`**.
- **CI triage helper:** `check_local_box_ci_runs.sh` forwards **`--branch`** to **`gh run list`**; **`--failed-only`** narrows to completed non-success, non-cancelled runs (mutually exclusive with **`--cancelled-only`**; cancelled gate alias: **`--fail-on-canceled`**); **`--latest-only --fail-on-failed`** (alias: **`--fail-on-non-success`**) gates branch health, **`--fail-on-incomplete`** (alias: **`--fail-on-non-completed`**) enforces settled runs, and **`--fail-on-empty`** fails when filters return no rows (shortcut: **`--gate-strict`** requires **`--branch`**).
- **Go-live tooling:** execution checklist, daily status reporter, `artifacts/go-live/` evidence layout; CI smoke + baseline require the tracked onboarding README.
- **CI pip UX:** job **check** runs **pip upgrade** and **`pip install -r requirements.txt`** as separate steps (clearer Actions logs) with **PIP_NO_INPUT** / **PIP_DISABLE_PIP_VERSION_CHECK** on the job.

### Recommended verifier commands

```bash
cd /path/to/project-anchor
./scripts/check_checklist_curl_guardrails.sh
./scripts/check_local_box_baseline.sh
./scripts/go_live_status_report.sh
```

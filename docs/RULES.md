# Project Anchor — operational rules (SSOT)

This file is the **single source of truth** for cross-cutting operational rules that must stay aligned across docs, scripts, and CI. Other documents should **summarize and link here** instead of inventing new wording.

**Enforcement:** `scripts/check_go_live_rules.sh` (run locally and in **`.github/workflows/local-box-baseline.yml`** job **`check`**). **`scripts/check_local_box_baseline.sh`** requires this path to exist (`REQUIRED_PATHS`).

---

## Go-live status reporter (`go_live_status_report.sh`)

- **CI (`local-box-baseline` / job `check`):** `go_live_status_report.sh` runs **stdout-only** (no `--out` file in Actions; workflow log is the artifact). Wording anchor for automated checks: **stdout-only**.
- **Local standup evidence:** use **`--out`** with a **file** path (directories and directory-like trailing slashes are rejected — see `./scripts/go_live_status_report.sh --help`). Wording anchor for automated checks: **`--out`**.
- **Execution board:** checklist and owners live in **`docs/GO_LIVE_CHECKLIST.md`**.
- **Evidence layout:** **`artifacts/go-live/README.md`** (tracked); `artifacts/go-live/*.out` is gitignored.

If you change the rules above, update **this file first**, then adjust summaries elsewhere and extend **`scripts/check_go_live_rules.sh`** if you add new machine-verifiable anchors.

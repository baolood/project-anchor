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

---

## Go-live checklist quality gates (`docs/GO_LIVE_CHECKLIST.md`)

These rules turn the checklist itself into a machine-checked artifact. Anchors below are matched verbatim by **`scripts/check_go_live_rules.sh`** — change them here first, then in the script.

- **WIP cap (§4):** maximum number of `IN_PROGRESS` items in §4 at any one time. Default **14** (snapshot at 2026-05-07). Override with env var `GOLIVE_WIP_LIMIT`. Lower the cap as items move to `DONE`; **raise it only via a §9 review minute** (no silent inflation). Wording anchor: **WIP cap**.
- **DONE evidence:** every `Status: DONE` row in §4 must carry an `Evidence:` line containing at least one verifiable anchor — a backtick-wrapped path (e.g. **`docs/...`**), a `§N` cross-reference, or `commit <sha>`. Placeholder `<link>` is rejected. Wording anchor: **DONE evidence**.
- **Risk ETA:** §6 risk rows with `Status: **OPEN**` and `ETA to close: **YYYY-MM-DD**` in the past fail this check. Either close the risk (`Status: **RESOLVED**`) or move the ETA forward in a §9 review minute. The script also prints a `[warn]` line when ETA is within the next 7 days. Wording anchor: **Risk ETA**.

- **WIP freeze (time-boxed, no silent cap inflation):** while `today <=` **WIP freeze until**, §4 `IN_PROGRESS` must stay at or below **WIP freeze baseline**, and **`GOLIVE_WIP_LIMIT` must not exceed that baseline** (override is for lowering the cap only, or unset). Machine-parsed lines (edit dates in §9 when rolling the freeze):
  - **WIP freeze baseline:** **14**
  - **WIP freeze until:** **2026-05-14** (inclusive; enforcement lifts on **2026-05-15**)
  - After the window ends, remove or roll forward these two lines in a §9 minute so the doc does not lie stale.

> Together these turn the checklist from a discipline document into a system constraint: new `IN_PROGRESS` cannot grow past the cap, `DONE` cannot be claimed without a real pointer, an aging risk forces a review instead of quietly slipping, and the one-week **WIP freeze** blocks “raise the limit in CI” without human intent recorded in **`docs/RULES.md`**.

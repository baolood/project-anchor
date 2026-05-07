# Environment parity checklist (parent repo)

Use this when satisfying **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 1 — **Prod-like environment parity check**. Goal: record **intentional** differences between local / CI / future stage-like hosts, not to pretend dev equals prod.

**Owner:** **baolood**. **Evidence:** keep this file updated; link the matching commit in the Week 1 row.

> Working notes are scoped to the **parent repo** (`local_box`, `shared`, `risk_engine`, parent `requirements.txt`). Subtree (`anchor-backend`) and submodule (`anchor-console`) parity belongs to their own repos.

## 1) Runtime identity

| Check | Local (this maintainer) | CI (`local-box-baseline` job `check`) | Stage / prod-like (target) | Match? |
|-------|-------------------------|----------------------------------------|----------------------------|--------|
| OS / arch | `Darwin 25.4.0 arm64` | `ubuntu-latest` (x86_64) | `<target env TBD>` | **N**: arch + OS differ — parent repo is platform-portable Python; flagged here so any platform-specific code is reviewed before stage. |
| Python **minor** | **3.8.10** | **3.11** (workflow `python-version`) | `<target env TBD>` | **N**: tracked as **§6 R-002** below. |
| `PYTHONPATH` for smokes | unset by default; `export PYTHONPATH=.` per `README.md` | `.` (job env) | `<target env TBD>` | **Y** when contributors follow the documented `export`. |

## 2) Dependencies

| Check | Local | CI | Stage / prod-like | Match? |
|-------|-------|----|--------------------|--------|
| Install source | `pip install -r requirements.txt` (root pinned file) | same | `<target env TBD>` | **Y** |
| Non-interactive pip | optional | `PIP_NO_INPUT=1`, `PIP_DISABLE_PIP_VERSION_CHECK=1` | `<target env TBD>` | **Y** in spirit; local devs are not required to set these. |
| Lock regeneration | `pip-compile requirements.in -o requirements.txt` (maintainers only) | not run in CI; CI consumes the committed lock | `<target env TBD>` | **Y** |

## 3) Data plane defaults (parent `local_box`)

| Check | Local | CI | Stage / prod-like | Match? |
|-------|-------|----|--------------------|--------|
| Default SQLite path | `<repo-root>/anchor.db` (verified via `event_store.DB_PATH`) | same default; smokes do not override | `<target env TBD>` | **Y** |
| `LOCAL_BOX_DB_PATH` override | unset on this maintainer machine | unset in CI | `<target env TBD>` | **Y** |
| SQLite version | `3.35.5` (system) | runner-provided (Ubuntu apt sqlite) | `<target env TBD>` | **Y** for `init_db` smoke; raise here if a feature requires a newer SQLite. |

## 4) Repo layout / guardrails

| Check | Local | CI | Stage / prod-like | Match? |
|-------|-------|----|--------------------|--------|
| `docs/RULES.md` present | **Y** | required by `check_local_box_baseline.sh` | n/a (CI gate) | **Y** |
| `docs/GO_LIVE_CHECKLIST.md` present | **Y** | reporter smoke | n/a (CI gate) | **Y** |
| `scripts/check_go_live_rules.sh` executable | **Y** | job `check` step | n/a (CI gate) | **Y** |
| `.githooks/pre-commit` installed (`git config core.hooksPath`) | **N** on this machine — install with `./scripts/install_git_hooks.sh` | n/a (CI runs scripts directly) | n/a | optional; documented in `CONTRIBUTING.md`. |

## 5) Intentional / known deltas (must be listed, not hidden)

1. **Python 3.8 (local) vs 3.11 (CI).** Treated as a **known divergence**; tracked in **§6 R-002** until aligned. Day-to-day rule: CI is source of truth for parent smokes. Don't claim "works on my machine" if CI hasn't run.
2. **OS/arch:** local `Darwin/arm64`, CI `ubuntu-latest/x86_64`, target `<TBD>`. Parent code is pure Python — flag any binary wheels or platform-specific paths added later.
3. **Local Git hooks optional.** `.githooks/pre-commit` is real protection only after `./scripts/install_git_hooks.sh`. CI guardrails do not depend on it.
4. **Stage / prod-like host: not yet defined.** Once it exists, fill the third column in §1–§4 and re-sign §5.

## 6) Sign-off

- Prepared by: **baolood** / **2026-05-07**
- Reviewed by: Release manager (**baolood**, interim) / pending after stage host is defined

When the **Stage / prod-like** column is filled and `§5` deltas are reviewed, update **`docs/GO_LIVE_CHECKLIST.md`** Week 1 parity item to `DONE` and link the commit that finalized this file.

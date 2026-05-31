# Environment parity checklist (parent repo)

Use this when satisfying **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 1 — **Prod-like environment parity check**. Goal: record **intentional** differences between local / CI / the current stage / prod-like target, not to pretend dev equals prod.

**Owner:** **baolood**. **Evidence:** keep this file updated; link the matching commit in the Week 1 row.

> Working notes are scoped to the **parent repo** (`local_box`, `shared`, `risk_engine`, parent `requirements.txt`). Subtree (`anchor-backend`) and submodule (`anchor-console`) parity belongs to their own repos. Current target host facts come from **`docs/STAGE_ENVIRONMENT_FACTS_V1.md`**.

## 1) Runtime identity

| Check | Local (this maintainer) | CI (`local-box-baseline` job `check`) | Stage / prod-like (target) | Match? |
|-------|-------------------------|----------------------------------------|----------------------------|--------|
| OS / arch | `Darwin 25.4.0 arm64` | `ubuntu-latest` (x86_64) | `Linux x86_64` on Vultr single-VM host `vultr` | **N**: local differs; CI and stage are both Linux/x86_64. |
| Python **minor** | **3.11.15** (`/opt/homebrew/bin/python3.11`) | **3.11** (workflow `python-version`) | default `python3` is **3.10.12**; parent baseline validated with **`python3.11`** (`3.11.0rc1`) | **Y** for the agreed parent-check path: explicit `PYTHON=python3.11` is now available and validated on the target host. |
| `PYTHONPATH` for smokes | unset by default; `export PYTHONPATH=.` per `README.md` | `.` (job env) | unset by default; `PYTHONPATH=.` verified for parent import smoke | **Y** when operators follow the documented `export`. |

## 2) Dependencies

| Check | Local | CI | Stage / prod-like | Match? |
|-------|-------|----|--------------------|--------|
| Install source | `pip install -r requirements.txt` (root pinned file) | same | clean git clone verified on target host; same root lock intended | **Y** |
| Non-interactive pip | optional | `PIP_NO_INPUT=1`, `PIP_DISABLE_PIP_VERSION_CHECK=1` | not yet explicitly recorded on host | **Y** in spirit; host-side convention still needs a concrete operator note. |
| Lock regeneration | `pip-compile requirements.in -o requirements.txt` (maintainers only) | not run in CI; CI consumes the committed lock | maintainers-only path; not exercised on host | **Y** |

## 3) Data plane defaults (parent `local_box`)

| Check | Local | CI | Stage / prod-like | Match? |
|-------|-------|----|--------------------|--------|
| Default SQLite path | `<repo-root>/anchor.db` (verified via `event_store.DB_PATH`) | same default; smokes do not override | `/root/project-anchor/anchor.db` | **Y** |
| `LOCAL_BOX_DB_PATH` override | unset on this maintainer machine | unset in CI | unset in read-only host fact collection | **Y** |
| SQLite version | `3.35.5` (system) | runner-provided (Ubuntu apt sqlite) | `3.37.2` | **Y** for current parent smokes; versions differ but no blocking feature gap is recorded. |

## 4) Repo layout / guardrails

| Check | Local | CI | Stage / prod-like | Match? |
|-------|-------|----|--------------------|--------|
| `docs/RULES.md` present | **Y** | required by `check_local_box_baseline.sh` | **Y** on target host checkout | **Y** |
| `docs/GO_LIVE_CHECKLIST.md` present | **Y** | reporter smoke | **Y** on target host checkout | **Y** |
| `scripts/check_go_live_rules.sh` executable | **Y** | job `check` step | **Y** on target host checkout | **Y** |
| `.githooks/pre-commit` installed (`git config core.hooksPath`) | **N** on this machine — install with `./scripts/install_git_hooks.sh` | n/a (CI runs scripts directly) | n/a | optional; documented in `CONTRIBUTING.md`. |

## 5) Intentional / known deltas (must be listed, not hidden)

1. **Host default `python3` still differs, but the parent validation path is now aligned.** Local parent evidence runs on **3.11.15**, CI runs **3.11**, and the stage target now has explicit **`python3.11`** (`3.11.0rc1`) available for parent baseline checks. The default host `python3` remains **3.10.12**, but that no longer blocks Week 1 parity because the agreed parent-check path is explicit `PYTHON=python3.11`.
2. **OS/arch differs across local vs CI/stage.** Local is `Darwin/arm64`; CI and the target host are `Linux/x86_64`. Parent code is pure Python — flag any binary wheels or platform-specific paths added later.
3. **Local Git hooks optional.** `.githooks/pre-commit` is real protection only after `./scripts/install_git_hooks.sh`. CI guardrails do not depend on it.
4. **Stage / prod-like host is now locked.** Use Vultr host `45.76.190.109` (`hostname: vultr`) as the shared Week 2–6 reference target until replaced by an explicit migration decision. Remaining blocker is parity completion, not target identity.

## 6) Sign-off

- Prepared by: **baolood** / **2026-05-07**
- Reviewed by: Release manager (**baolood**, interim) / target host defined and explicit `python3.11` parent-check path validated on `2026-05-31`

Week 1 parity may now be treated as `DONE` for the parent repo because the target host is fixed and the explicit `python3.11` parent-check path has been validated. Future host-change work may still choose to switch the default `python3`, but that is no longer required for this checklist row.

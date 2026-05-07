# Environment parity checklist (parent repo)

Use this when satisfying **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 1 — **Prod-like environment parity check**. Goal: record **intentional** differences between local / CI / future stage-like hosts, not to pretend dev equals prod.

**Owner:** fill name in the go-live board. **Evidence:** paste or link completed rows (redacted) in the Week 1 item.

## 1) Runtime identity

| Check | Local | CI (`local-box-baseline` job `check`) | Stage / prod-like (target) | Match? |
|-------|-------|----------------------------------------|----------------------------|--------|
| OS / arch | | `ubuntu-latest` | | |
| Python **minor** (must match CI for parent smokes) | | **3.11** (workflow `python-version`) | | |
| `PYTHONPATH` for smokes | | `.` (job env) | | |

## 2) Dependencies

| Check | Local | CI | Stage / prod-like | Match? |
|-------|-------|----|--------------------|--------|
| Install source | `pip install -r requirements.txt` | same | | |
| Non-interactive pip | optional | `PIP_NO_INPUT=1`, `PIP_DISABLE_PIP_VERSION_CHECK=1` | | |

## 3) Data plane defaults (parent `local_box`)

| Check | Local | CI | Stage / prod-like | Match? |
|-------|-------|----|--------------------|--------|
| Default SQLite path (`anchor.db` at repo root) | | smokes use default unless env set | | |
| `LOCAL_BOX_DB_PATH` override | | usually unset in CI | | |

## 4) Repo layout / guardrails

| Check | Local | CI | Stage / prod-like | Match? |
|-------|-------|----|--------------------|--------|
| `docs/RULES.md` present | | required by `check_local_box_baseline.sh` | | |
| `docs/GO_LIVE_CHECKLIST.md` present | | reporter smoke | | |
| `check_go_live_rules.sh` | | job `check` step | | |

## 5) Intentional deltas (must be listed, not hidden)

Document anything that **will** differ in prod-like (paths, secrets, URLs, Docker vs bare metal, submodule SHAs):

1. …
2. …

## Sign-off

- Prepared by: `<name>` / `<date>`
- Reviewed by: Release manager / `<date>`

When this table is complete and reviewed, update **`docs/GO_LIVE_CHECKLIST.md`** Week 1 parity item to `DONE` and attach this file (or a copy in your ticket system).

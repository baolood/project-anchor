# Stage deploy runbook (draft — Week 2)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 2 — **One-command deployment runbook validated** until a real stage host and timings are recorded.

**Owner:** **baolood** (Engineering lead, interim).

**Scope:** this runbook covers bringing up the **default local/stage stack** described in **`RUNBOOK.md`** → **Daily Mode** (`anchor-backend` via Docker Compose). It does **not** replace subtree/submodule release processes inside **`anchor-backend/`** or **`anchor-console/`** — those stay in their own repos; this parent doc only wires the **orchestration path** you use from a clean clone.

## Preconditions (record actuals in evidence)

| Check | Expected | Your value |
|-------|----------|------------|
| Clean checkout | `git status` clean on intended SHA | |
| Python (parent smokes / `local_box`) | Match CI **3.11** when touching parent Python — see **`docs/GO_LIVE_CHECKLIST.md`** §6 **R-002** | |
| Docker / Compose | `docker compose version` works | |
| `anchor-backend` subtree | present at `anchor-backend/` | |

## One-command path (default Daily Mode)

From repo root (portable placeholder):

```bash
cd /path/to/project-anchor/anchor-backend
docker compose up -d --build
docker compose stop worker 2>/dev/null || true
sleep 2
docker compose up -d worker
```

**Rationale:** mirrors **`RUNBOOK.md`** → **Daily Mode** → **Start (backend + worker)** with `docker-compose.override.yml` when present.

## Post-deploy smoke (minimum)

Run from **repo root** after the stack is up (adjust URLs if your compose maps different ports):

```bash
cd /path/to/project-anchor
export PYTHONPATH=.
python3 -m pip install -r requirements.txt
./scripts/check_local_box_baseline.sh
./scripts/check_go_live_rules.sh
# Optional: hit backend health if defined in anchor-backend docs (fill when stage URL is fixed)
```

## Duration baseline (fill on first real validation)

| Step | Started (UTC) | Finished (UTC) | Wall seconds | Notes |
|------|-----------------|----------------|----------------|-------|
| `docker compose up -d --build` | | | | |
| worker recycle | | | | |
| parent smoke block | | | | |

## Acceptance vs go-live board

- **Stage deploy from clean checkout succeeds:** tick when the compose block completes without error **and** post-deploy smokes pass (or document which smoke is N/A and why).
- **Duration baseline recorded:** fill the table above on the first successful run; update when hardware or compose changes.

## Rollback pointer

See **`docs/RELEASE_BRANCH_POLICY.md`** (tags + revert/redeploy). After a failed deploy, capture the rollback path used in the Week 2 **Rollback drill** row.

## Sign-off

- Draft author: **baolood** / **2026-05-07**
- First validated run: `<name>` / `<date>` — attach compose logs + filled duration table + smoke output

When this runbook is validated on a real stage host, update **`docs/GO_LIVE_CHECKLIST.md`** Week 2 row to `DONE` and link the commit or ticket that holds the evidence bundle.

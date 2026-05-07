# Rollback drill runbook (draft — Week 2)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 2 — **Rollback drill completed** until a real drill runs and timings are recorded.

**Owner:** **baolood** (Operations lead, interim).

**Pairs with:**

- **`docs/STAGE_DEPLOY_RUNBOOK.md`** (forward / one-command deploy path)
- **`docs/RELEASE_BRANCH_POLICY.md`** (tags + branch policy)
- **`RUNBOOK.md`** → Daily Mode (compose orchestration commands)

> Scope: parent repo orchestration of **`anchor-backend/`** via Docker Compose. Database backup/restore drills are tracked separately in §4 Week 4 — this drill validates that **redeploy / revert** can return service to a known-good state, not data recovery.

## Preconditions (record actuals in evidence)

| Check | Expected | Your value |
|-------|----------|------------|
| Forward path validated first | `docs/STAGE_DEPLOY_RUNBOOK.md` first run signed off | |
| Known-good rollback target | tag (`vX.Y.Z`) or commit SHA | |
| Recovery target (agreed) | wall-time budget (e.g. **≤ 10 min**) | |
| Notification channel | who watches drill output / on-call ack | |

## Drill scenario

The drill must cover **both directions** in one session:

1. **Roll forward** — deploy a deliberately new commit on `main` using `docs/STAGE_DEPLOY_RUNBOOK.md`.
2. **Roll back** — return service to the previous known-good revision using one of:
   - **Tag-based redeploy:** `git checkout <previous tag>` and re-run the deploy block.
   - **Revert merge:** `git revert -m 1 <merge commit>` on `main` (PR + CI green per **`docs/RELEASE_BRANCH_POLICY.md`**), then re-run the deploy block.

Pick **one** path per drill row below; record which path was used.

## Drill log (fill on first real run)

| Step | Started (UTC) | Finished (UTC) | Wall seconds | Notes |
|------|-----------------|----------------|----------------|-------|
| 1. Roll forward (deploy new SHA) | | | | |
| 2. Decision: revert vs redeploy | | | | which path + why |
| 3. Apply rollback | | | | command(s) used |
| 4. Service back to known-good | | | | smoke output snippet |
| **Total recovery wall time** | — | — | | must be ≤ agreed target |

## Smoke after rollback (minimum)

```bash
cd /path/to/project-anchor
export PYTHONPATH=.
./scripts/check_local_box_baseline.sh
./scripts/check_go_live_rules.sh
# Backend health check (fill exact URL/port once stage is defined):
# curl --connect-timeout 5 --max-time 20 http://<stage-host>:<port>/healthz
```

If the smoke fails after rollback, the drill is **NOT** considered complete — declare incident and escalate per Week 2 on-call SOP draft.

## Acceptance vs go-live board

- **Roll forward + rollback both tested:** tick when both legs of the drill complete cleanly.
- **Recovery under agreed limit:** tick only when **Total recovery wall time** in the drill log is **≤** the agreed target.
- Attach the filled drill log + post-rollback smoke output to the Week 2 row evidence.

## Sign-off

- Draft author: **baolood** / **2026-05-07**
- First completed drill: `<name>` / `<date>` — attach drill log + smoke output + which rollback path was used (revert merge vs tag redeploy)

When the drill log is filled and smoke is GREEN within the agreed limit, update **`docs/GO_LIVE_CHECKLIST.md`** Week 2 “Rollback drill completed” row to `DONE` and link the commit / ticket holding the evidence bundle. Until then, this runbook itself is the working evidence.

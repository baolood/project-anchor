# Rollback drill runbook (draft — Week 2)

**Status:** completed baseline for Week 2 rollback drill — agreed recovery target fixed and destructive rollback execution judged within target.

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
| Recovery target (agreed) | wall-time budget (e.g. **≤ 10 min**) | **≤ 10 min** |
| Notification channel | who watches drill output / on-call ack | |

## Drill scenario

The drill must cover **both directions** in one session:

1. **Roll forward** — deploy a deliberately new commit on `main` using `docs/STAGE_DEPLOY_RUNBOOK.md`.
2. **Roll back** — return service to the previous known-good revision using one of:
   - **Tag-based redeploy:** `git checkout <previous tag>` and re-run the deploy block.
   - **Revert merge:** `git revert -m 1 <merge commit>` on `main` (PR + CI green per **`docs/RELEASE_BRANCH_POLICY.md`**), then re-run the deploy block.

Pick **one** path per drill row below; record which path was used.

## Drill log (first destructive execution recorded; recovery target still pending)

| Step | Started (UTC) | Finished (UTC) | Wall seconds | Notes |
|------|-----------------|----------------|----------------|-------|
| 1. Roll forward (deploy new SHA) | 2026-05-31T14:48:30+00:00 | 2026-05-31T14:49:17+00:00 | ~47 | Controlled deploy validation to host checkout `deda43e`; see `docs/ONE_COMMAND_DEPLOYMENT_RUNBOOK_FIRST_CONTROLLED_VALIDATION_CLOSEOUT_V1.md`. |
| 2. Decision: revert vs redeploy | 2026-06-01T01:41:03+00:00 | 2026-06-01T01:41:50+00:00 | ~47 | Decision-only drill selected checkout-based rollback to `d76bb0a`; see `docs/ROLLBACK_DRILL_FIRST_CONTROLLED_VALIDATION_CLOSEOUT_V1.md`. |
| 3. Apply rollback | 2026-06-01T02:12:03+00:00 | 2026-06-01T02:12:29+00:00 | 26 | Checkout-based destructive rollback from `deda43e` to `d76bb0a`, then bounded deploy path. |
| 4. Service back to known-good | 2026-06-01T02:12:29+00:00 | 2026-06-01T02:12:48+00:00 | 19 | `/health` OK, `/ops/state` reachable, worker heartbeat fresh, baseline PASS. |
| **Total recovery wall time** | 2026-06-01T02:12:03+00:00 | 2026-06-01T02:12:29+00:00 | 26 | Captured successfully; within agreed target **≤ 10 min**. |

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
- First controlled validation (decision-only): **baolood** / **2026-06-01** — see **`docs/ROLLBACK_DRILL_FIRST_CONTROLLED_VALIDATION_CLOSEOUT_V1.md`**
- First destructive execution drill: **baolood** / **2026-06-01** — see **`docs/ROLLBACK_DRILL_FIRST_DESTRUCTIVE_EXECUTION_CLOSEOUT_V1.md`**
- Recovery target decision: **baolood** / **2026-06-01** — see **`docs/ROLLBACK_RECOVERY_TARGET_DECISION_V1.md`**
- First completed drill: **baolood** / **2026-06-01** — destructive rollback path executed to `d76bb0a`, smoke GREEN, recovery time `26s` within agreed target `≤ 10 min`

The drill log is now filled, smoke is GREEN, and the observed recovery time is within the agreed limit. Use this runbook together with the linked closeouts as the evidence bundle for Week 2 rollback completion.

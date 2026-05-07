# Data migration rollback runbook (draft — Week 4)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 4 — **Data migration rollback path verified** until at least one **controlled** rollback test from a post-migration state is executed in a test environment and evidence is attached.

**Owner:** **baolood** (Data/DB owner, interim).

**Pairs with:** **`docs/BACKUP_AND_RECOVERY.md`** (pre-migration backup is mandatory), **`docs/RESTORE_DRILL_RUNBOOK.md`** (if rollback = restore-from-backup rather than schema down), **`anchor-backend/`** subtree migration tooling (fill exact commands when known).

> Rollback is not “hope `git revert` fixes the DB.” It is a **rehearsed path** from a known bad migration state back to a known-good schema + data boundary.

---

## 1) Preconditions (record in evidence)

| Check | Pass? | Notes |
|-------|-------|-------|
| Forward migration script / version id is frozen for the drill | ☐ | link migration ticket |
| Pre-migration backup exists per **`docs/BACKUP_AND_RECOVERY.md`** | ☐ | artifact id + timestamp |
| Test DB is disposable or restorable from backup in **≤ RTO** | ☐ | |
| Rollback owner + witness identified | ☐ | Data/DB + Engineering lead |

---

## 2) Choose rollback strategy (pick one per drill)

| Strategy | When to use | Primary artifact |
|----------|---------------|------------------|
| **S1 — Down migration** | ORM / framework supports reversible migrations | `down.sql` / `alembic downgrade` / `<TBD>` |
| **S2 — Restore from backup** | Irreversible DDL or data rewrite | backup from §1 + **`docs/RESTORE_DRILL_RUNBOOK.md`** Drill B |
| **S3 — Re-deploy previous image + DB snapshot** | Containerized stack with volume snapshot | image tag + volume snapshot id |

Document the chosen strategy letter in the drill log.

---

## 3) Drill log — forward then rollback

| Step | Started (UTC) | Finished (UTC) | Notes |
|------|-----------------|----------------|-------|
| M1. Apply forward migration to test DB | | | command / ticket link |
| M2. Verify schema version / migration table reflects new revision | | | |
| M3. Simulate failure condition (app smoke fails OR explicit abort) | | | |
| M4. Execute rollback (**S1 / S2 / S3**) | | | exact commands |
| M5. Verify schema version returned + critical queries GREEN | | | |
| M6. Compare checksums on invariant tables vs pre-M1 baseline | | | |

**Pass criteria:** M5 and M6 GREEN; no orphan objects that break the next forward migration attempt.

---

## 4) Failure modes to rehearse at least once

- **Partial migration** (process killed mid-flight) — rollback must still land clean.
- **Long-running migration** — confirm locks/timeouts do not block rollback window beyond **RTO**.

---

## 5) Acceptance vs go-live board

- **At least one rollback test from migration state:** §3 log complete for one chosen strategy (**S1**, **S2**, or **S3**).
- Evidence must include commands (or console URLs) and before/after schema versions.

---

## 6) Sign-off

- Drill lead: **baolood** / `<date>`
- Witness (Engineering lead): `<name>` / `<date>`

When §3 is filled and pass criteria are met, update **`docs/GO_LIVE_CHECKLIST.md`** Week 4 “Data migration rollback path verified” row to `DONE` and link the evidence bundle.

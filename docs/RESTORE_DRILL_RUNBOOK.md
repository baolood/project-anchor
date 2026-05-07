# Restore drill runbook (draft — Week 4)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 4 — **Restore drill (table-level + full restore)** until both drill legs complete in a **test environment** and RPO/RTO are measured against agreed targets.

**Owner:** **baolood** (Data/DB owner, interim).

**Pairs with:** **`docs/BACKUP_AND_RECOVERY.md`** (RPO/RTO targets, backup artifacts), **`docs/GO_LIVE_CHECKLIST.md`** §5 **G3** (backup/restore drill gate).

> This drill proves **recovery**, not just that backups exist. Run only against disposable data or a dedicated restore sandbox — never against production without explicit release manager approval.

---

## 1) Preconditions (record in evidence)

| Check | Pass? | Notes |
|-------|-------|-------|
| Backup artifacts exist for each **Asset ID** in **`docs/BACKUP_AND_RECOVERY.md`** §1 | ☐ | list artifact IDs / timestamps |
| Test environment is isolated from prod traffic | ☐ | hostname / compose project name |
| Restore operator has least-privilege credentials | ☐ | role names |
| On-call aware (if drill could page) | ☐ | per **`docs/ON_CALL_SOP.md`** |

---

## 2) Drill A — Table-level restore (logical subset)

**Goal:** restore **one** business-critical table (or small row set) from backup into the test DB without full wipe.

| Step | Started (UTC) | Finished (UTC) | Notes |
|------|-----------------|----------------|-------|
| A1. Record pre-restore checksum / row count for target table | | | |
| A2. Apply intentional corruption or delete in test only | | | |
| A3. Restore subset from backup (document exact command / console path) | | | |
| A4. Verify row count + checksum match pre-corruption | | | |

**Pass criteria:** A4 matches within agreed tolerance; no unrelated tables damaged.

---

## 3) Drill B — Full restore (clean slate)

**Goal:** prove you can rebuild the **entire** database service from backup onto empty storage.

| Step | Started (UTC) | Finished (UTC) | Notes |
|------|-----------------|----------------|-------|
| B1. Snapshot or export “known good” test baseline | | | |
| B2. Wipe test DB volume / drop database (test only) | | | |
| B3. Full restore from latest **eligible** backup | | | command / vendor flow |
| B4. Run application smoke (migrations if applicable) | | | link smoke log |
| B5. Compare critical table checksums vs B1 baseline | | | |

**Pass criteria:** B5 matches; B4 smoke GREEN.

---

## 4) RPO / RTO measurement

| Metric | Target (from **`docs/BACKUP_AND_RECOVERY.md`** §5) | Measured value | Pass? |
|--------|-----------------------------------------------------|----------------|-------|
| **RPO** | `<agreed>` | max clock skew between last good commit and restored data | ☐ |
| **RTO** | `<agreed>` | wall time from “restore start” declared → B4 smoke GREEN | ☐ |

If measured values exceed targets, file **`docs/GO_LIVE_CHECKLIST.md`** §6 risk and reschedule drill — **do not** mark this row `DONE`.

---

## 5) Acceptance vs go-live board + §5 G3

- **Successful restore in test environment:** both §2 Drill A and §3 Drill B **Pass criteria** GREEN.
- **RPO/RTO measured and within target:** §4 table GREEN.
- **§5 G3** cannot be marked GREEN until this Week 4 row is `DONE` with evidence attached.

---

## 6) Sign-off

- Drill lead: **baolood** / `<date>`
- Witness (Release manager): `<name>` / `<date>`

When evidence is attached, update **`docs/GO_LIVE_CHECKLIST.md`** Week 4 “Restore drill” row to `DONE` and link the commit / ticket with filled tables.

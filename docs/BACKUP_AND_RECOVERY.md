# Backup and recovery strategy (draft — Week 4)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 4 — **Backup strategy implemented** until schedule, retention, and verification are agreed and executed at least once in a test environment.

**Owner:** **baolood** (Data/DB owner, interim).

**Pairs with:** **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 4 (restore drill + migration rollback), **`RUNBOOK.md`**, **`docs/ENVIRONMENT_PARITY_CHECKLIST.md`** (SQLite / DB paths).

---

## 1) Backup scope (what must never be lost)

| Asset ID | Description | Primary location today | Backup target |
|----------|-------------|-------------------------|----------------|
| **DB-PARENT** | Parent repo SQLite (`local_box` audit) | default `<repo-root>/anchor.db` (or `LOCAL_BOX_DB_PATH`) | object store / encrypted volume snapshot |
| **DB-BACKEND** | **`anchor-backend`** application database (if not SQLite) | `<TBD>` (compose volume / managed DB) | vendor-native backup or logical dump |
| **CFG-RUNTIME** | Non-secret runtime config that cannot be reconstructed from git | `<TBD>` | versioned alongside DB backup |
| **SECRETS** | API keys, TLS material, DB passwords | secret manager only — **never** in git | secret-manager backup / export policy per vendor |

**Rule:** anything not reconstructible from **`git` + `requirements.txt` + documented env** is in scope for §1.

---

## 2) Schedule and retention (placeholders — fill before `DONE`)

| Asset ID | Frequency | Retention | Encryption at rest | Verification cadence |
|----------|-----------|-----------|----------------------|------------------------|
| **DB-PARENT** | daily at `<TBD UTC>` | **30 days** rolling | **required** | weekly restore smoke on copy |
| **DB-BACKEND** | per vendor default or **hourly** if high churn | **30 days** minimum | **required** | monthly full restore drill |
| **CFG-RUNTIME** | on change + daily | match DB | **required** | quarterly diff review |

---

## 3) Backup procedure (logical dump pattern — SQLite / portable)

**Parent `anchor.db` (example — adjust paths):**

```bash
# From repo root; use UTC timestamp in artifact name
ts="$(date -u +%Y%m%dT%H%M%SZ)"
sqlite3 "${LOCAL_BOX_DB_PATH:-anchor.db}" ".backup 'artifacts/go-live/backup_anchor_${ts}.db'"
```

> **Git policy:** do **not** commit backup files by default. Store in encrypted object storage or a dedicated backup host. If a sample must live in git, use a redacted fixture path and document the exception in the PR.

**Managed DB / Docker volume:** replace with vendor runbook (RDS snapshot, `pg_dump`, etc.) — document the exact command or console path here when known.

---

## 4) Verification (must run before Week 4 row → `DONE`)

1. **List restore** — prove you can list available backups for each **Asset ID**.
2. **Integrity** — checksum or vendor integrity check on a randomly picked backup artifact.
3. **Access** — only roles in **`docs/GO_LIVE_CHECKLIST.md`** §2 Data/DB + Operations can read backups.

Record outputs in the Week 4 evidence bundle (ticket or PR).

---

## 5) RPO / RTO targets (link to restore drill)

| Metric | Target (placeholder) | How measured |
|--------|------------------------|--------------|
| **RPO** | **≤ 1 h** for **DB-BACKEND**; **≤ 24 h** for **DB-PARENT** (tune with product) | max acceptable data loss window |
| **RTO** | **≤ 4 h** to return read/write API | wall clock from incident declare → verified healthy |

These numbers are **not agreed** until Release manager signs **`docs/SERVICE_SLI_SLO.md`** + this doc together. The **Restore drill** row must prove them.

---

## 6) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Reviewed by (Release manager): `<name>` / `<date>`
- Reviewed by (Data/DB owner): `<name>` / `<date>`

When §2 is filled, §4 verification is executed, and §5 targets are agreed, update **`docs/GO_LIVE_CHECKLIST.md`** Week 4 “Backup strategy implemented” row to `DONE` and link the evidence commit / ticket.

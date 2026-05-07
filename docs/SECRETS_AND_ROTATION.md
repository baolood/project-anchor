# Secret management and key rotation (draft — Week 5-6)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 5-6 — **Secret management and key rotation policy** until §1 inventory is complete, **no-plaintext** scan is GREEN, and at least one rotation has been rehearsed end-to-end.

**Owner:** **baolood** (Security owner, interim).

**Pairs with:** **`docs/GO_LIVE_CHECKLIST.md`** §5 **G4** (security review gate), **`PR_DESCRIPTION.md`** checklist (secrets row), **`docs/BACKUP_AND_RECOVERY.md`** (secret-store backup policy).

> Do **not** paste real secret values into this file or anywhere in git. This document only describes **what** secrets exist, **where** they live, and **how** they rotate.

---

## 1) Secret inventory (fill before sign-off)

| Secret ID | Description | Storage today | Owner role | Rotation interval |
|-----------|-------------|----------------|------------|---------------------|
| **SEC-DB-BACKEND** | Application DB password / DSN | `<TBD secret manager>` | Data/DB owner | **90 days** or on suspected exposure |
| **SEC-API-KEY** | External API keys (per upstream) | `<TBD secret manager>` | Security owner | **90 days** |
| **SEC-TLS** | TLS cert + private key | `<TBD certificate authority>` | Operations lead | per CA validity (e.g. 90 days for ACME) |
| **SEC-SIGNING** | Internal signing keys (e.g. ticket signature) | `<TBD>` | Security owner | **180 days** |
| **SEC-CI** | CI tokens (GH PATs, deploy tokens) | GitHub repo / org secret store | Release manager | **90 days** |

**Rule:** anything that grants production access **must** appear here before M1 launch.

---

## 2) "No plaintext in repo / config" verification

Run on the parent repo before each release wave (and as a pre-merge habit):

```bash
# Parent repo guardrails already enforce most policy. Add a targeted scan:
git grep -nE 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|secret[_-]?key\s*=' -- ':!docs/' ':!RELEASE_NOTES.md' || true
```

**Scope rules:**

- Documentation files (e.g. **`docs/`**, **`RELEASE_NOTES.md`**) may contain **examples** that are clearly placeholders — flag any real-looking values during review.
- Subtree (**`anchor-backend/`**) and submodule (**`anchor-console/`**) maintain their own scans; record which scans ran in the Week 5-6 evidence bundle.

If the scan returns any line that is not an obvious placeholder, treat as **P1** (per **`docs/ON_CALL_SOP.md`**) until rotated and purged.

---

## 3) Rotation procedure (per secret ID)

For each row in §1, document the runbook columns when known:

| Secret ID | Pre-rotation | Rotate | Post-rotation |
|-----------|---------------|---------|----------------|
| **SEC-DB-BACKEND** | snapshot DB; warn on-call | issue new credential in secret manager; update consumers; revoke old | smoke + connection test |
| **SEC-API-KEY** | confirm vendor allows overlap window | create v2 key; rollout consumers; revoke v1 | upstream call smoke |
| **SEC-TLS** | obtain new cert in advance | swap; reload service | TLS verify + cert chain test |
| **SEC-SIGNING** | publish new key id; coexist | start signing with new id | verify old + new accepted during window |
| **SEC-CI** | create new PAT scoped minimally | swap GH secret; trigger workflow | CI green |

---

## 4) Required rehearsal before sign-off

Pick **one** secret ID from §1 (recommend **SEC-CI** because it touches CI without prod blast radius). Execute §3 row end-to-end, including the post-rotation verification. Record:

- Pre-rotation timestamp and operator
- Rotation completion timestamp
- Post-rotation verification log link
- Any consumer that needed manual intervention

---

## 5) Acceptance vs go-live board + §5 G4

- **No plaintext secrets in repo/config:** §2 scan run, output recorded, no real values found (or all rotated and purged).
- **Rotation procedure tested:** §4 rehearsal evidence attached.
- **§5 G4** cannot be GREEN until both criteria are met.

---

## 6) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Reviewed by (Security owner): `<name>` / `<date>`
- Reviewed by (Release manager): `<name>` / `<date>`

When inventory is complete, scan is clean, and one rotation is rehearsed, update **`docs/GO_LIVE_CHECKLIST.md`** Week 5-6 “Secret management and key rotation policy” row to `DONE` and link the evidence bundle.

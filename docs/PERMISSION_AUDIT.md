# Permission minimization + audit (draft — Week 5-6)

**Status:** draft — satisfies **`docs/GO_LIVE_CHECKLIST.md`** §4 Week 5-6 — **Permission minimization and audit** until §1 inventory is complete, §3 reductions are applied with diff evidence, and a §4 audit cadence is agreed.

**Owner:** **baolood** (Security owner, interim).

**Pairs with:** **`docs/GO_LIVE_CHECKLIST.md`** §5 **G4** (security review gate), **`docs/SECRETS_AND_ROTATION.md`** (every reduction in scope here may simplify rotation impact), **`docs/GITHUB_BRANCH_PROTECTION.md`** (repo write access is in scope).

> Principle: **least privilege by default**. Every account or token should justify why it has any permission beyond `read`.

---

## 1) Permission inventory (fill before sign-off)

| Subject ID | Type | Where it has access | Current scope | Justification | Reduction target |
|------------|------|----------------------|----------------|----------------|--------------------|
| **PRINC-OWNER** | human | GitHub repo + Settings | admin | sole maintainer (interim) | unchanged until co-maintainer added |
| **PRINC-CI** | service token | GitHub Actions | repo `read` + workflow | enables CI runs | confirm no `write` on `main` outside merge |
| **PRINC-DEPLOY** | service account / key | future stage host | `<TBD>` | runs deploy via **`docs/STAGE_DEPLOY_RUNBOOK.md`** | scope to deploy paths only |
| **PRINC-DB** | DB role | application DB | `<TBD>` | application R/W | split into reader vs writer if feasible |
| **PRINC-OPS** | on-call humans | runtime hosts / consoles | `<TBD>` | incident response | time-boxed elevation rather than standing admin |

---

## 2) Inputs to inspect

- GitHub: **Settings → Collaborators / Teams**, **Settings → Actions** (workflow permissions), **personal access tokens** in org / **`SEC-CI`** per **`docs/SECRETS_AND_ROTATION.md`**.
- Cloud / hosting console (when stage exists): IAM users, roles, service accounts, key pairs.
- DB: roles, default privileges, public schema rights.
- Internal tools: dashboards, secret managers, log stores.

Record where each subject is **defined** (link / console path) so the reduction in §3 has a verifiable target.

---

## 3) Reduction actions (each must have before/after evidence)

For every row in §1, log the reduction performed:

| Subject ID | Before | After | Operator | Evidence link |
|------------|--------|-------|----------|----------------|
| **PRINC-CI** | | | | |
| **PRINC-DEPLOY** | | | | |
| **PRINC-DB** | | | | |
| **PRINC-OPS** | | | | |

“No change required” is a valid value **only** with a one-line justification.

---

## 4) Audit cadence (post go-live)

- **Quarterly** review of §1 (every 3 months from M1 launch). Record review in **`docs/GO_LIVE_CHECKLIST.md`** §6 if any subject grew permissions without ticket.
- **Trigger reviews** any time a new subject is added or an existing one is escalated.

---

## 5) Acceptance vs go-live board + §5 G4

- **Service/account permissions reviewed and reduced:** §1 inventory complete and §3 has at least one row with applied reduction (or signed “no change required” with justification).
- **§5 G4** cannot be GREEN until this row is `DONE` together with **`docs/SECRETS_AND_ROTATION.md`**.

---

## 6) Sign-off

- Draft author: **baolood** / **2026-05-07**
- Reviewed by (Security owner): `<name>` / `<date>`
- Reviewed by (Release manager): `<name>` / `<date>`

When the inventory is filled and §3 has evidence rows, update **`docs/GO_LIVE_CHECKLIST.md`** Week 5-6 “Permission minimization and audit” row to `DONE` and link the evidence bundle.

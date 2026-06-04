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
| **PRINC-DEPLOY** | operator host access | single stage host deploy path | trusted operator root access on `vultr` stage host limited to bounded deploy / rollback work under `/root/project-anchor` and `/root/project-anchor/anchor-backend` | runs bounded deploy / rollback flows already validated in stage evidence | scope to deploy paths only; move to dedicated deploy user if host surface expands |
| **PRINC-DB** | DB role | stage application DB | application role for backend / worker against `anchor`; bounded admin access only during authorized drill paths | application R/W and bounded recovery / ops checks | split into reader vs writer if feasible when a distinct read-only app path exists |
| **PRINC-OPS** | on-call humans | runtime hosts / consoles | trusted operator-only access in solo internal review mode for bounded incident handling and safety controls | incident response | time-boxed elevation rather than standing admin once staffing splits |

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
| **PRINC-CI** | GitHub Actions policy allowed all actions | `allowed_actions=selected`, GitHub-owned actions only, verified actions disabled | baolood | **`docs/G4_ACTIONS_ALLOWED_ACTIONS_POLICY_BOUNDED_MUTATION_CLOSEOUT_V1.md`** |
| **PRINC-DEPLOY** | trusted operator host access on single stage host for bounded deploy / rollback work | no change required for current phase — single stage host only, no broader deploy surface exists yet | baolood | **`docs/STAGE_DEPLOY_RUNBOOK.md`**, **`docs/G1_DEPLOYMENT_ROLLBACK_GATE_RECONCILIATION_REVIEW_V1.md`**, **`docs/G4_PERMISSION_INVENTORY_SUBJECT_RECONCILIATION_V1.md`** |
| **PRINC-DB** | application DB role plus bounded drill-time admin access in stage stack | no change required for current phase — no separate read-only app path exists yet | baolood | **`docs/G3_FIRST_BOUNDED_RESTORE_DRILL_EXECUTION_CLOSEOUT_V1.md`**, **`docs/G4_PERMISSION_INVENTORY_SUBJECT_RECONCILIATION_V1.md`** |
| **PRINC-OPS** | trusted operator-only host / console access in solo internal review mode | no change required for current phase — staffing has not split and no separate elevation broker exists yet | baolood | **`docs/ON_CALL_SOP.md`**, **`docs/CLOUD_HOST_ACCESS_CLASS_MATRIX_V1.md`**, **`docs/G4_PERMISSION_INVENTORY_SUBJECT_RECONCILIATION_V1.md`** |

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

The current bounded project-phase audit inventory is now reconciled. If a new
subject is added or any subject expands scope, refresh §1 and §3 before the next
security sign-off.

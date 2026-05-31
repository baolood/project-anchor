# Release branch policy

**Status:** active — GitHub **branch protection** on `main` is now enforced for admins, required checks remain **`check`** and **`checklist-curl-guardrails`**, and the PR-only path has been re-verified after enforcement.

## Default branch

- **`main`** is the integration branch for this parent repo.

## Merge discipline

- **Required workflow:** all changes land via **pull request**; **`local-box-baseline`** (jobs **`checklist-curl-guardrails`** and **`check`**) must remain **required** on `main` before merge.
- **Admin bypass:** **`enforce_admins`** is enabled on `main`, so the same protection posture applies to admins as well as non-admin contributors.
- **Verification record:** PR-only flow was verified before enforcement via PR **#13**, and re-verified after enforcement via PR **#14** and PR **#15**.

## Tags and rollback

- **Release tags:** `vMAJOR.MINOR.PATCH` on commits that are intended rollback anchors (document the tag in the release PR / **`RELEASE_NOTES.md`**).
- **Rollback:** revert the merge commit on `main` **or** redeploy from the previous tag, whichever matches your runtime; record which path was used in the incident or release notes.
- **Drill procedure:** see **`docs/ROLLBACK_DRILL_RUNBOOK.md`** (Week 2 go-live board) for the structured roll-forward / roll-back drill, log table, and smoke step.

## Submodules / subtrees

- **Submodule / subtree pointers** (e.g. **`anchor-console/`**, **`anchor-backend/`**) ship as part of the parent repo commit — bump them only in dedicated PRs with explicit verification steps in the PR body.

# Release branch policy (draft)

**Status:** draft — GitHub **branch protection** on `main` must still be applied per **`docs/GITHUB_BRANCH_PROTECTION.md`**. Until that is GREEN, treat direct pushes to `main` as **technical debt** tracked in **`docs/GO_LIVE_CHECKLIST.md`** §6 (**R-001**).

## Default branch

- **`main`** is the integration branch for this parent repo.

## Merge discipline

- **Target:** all changes land via **pull request**; **`local-box-baseline`** (jobs **`checklist-curl-guardrails`** and **`check`**) must be **required** on `main` before merge.
- **Interim:** if protection is not yet enabled, every maintainer must still run the same order locally as CI (**`README.md`** → CI / **`CONTRIBUTING.md`** → local repro) before push.

## Tags and rollback

- **Release tags:** `vMAJOR.MINOR.PATCH` on commits that are intended rollback anchors (document the tag in the release PR / **`RELEASE_NOTES.md`**).
- **Rollback:** revert the merge commit on `main` **or** redeploy from the previous tag, whichever matches your runtime; record which path was used in the incident or release notes.
- **Drill procedure:** see **`docs/ROLLBACK_DRILL_RUNBOOK.md`** (Week 2 go-live board) for the structured roll-forward / roll-back drill, log table, and smoke step.

## Submodules / subtrees

- **Submodule / subtree pointers** (e.g. **`anchor-console/`**, **`anchor-backend/`**) ship as part of the parent repo commit — bump them only in dedicated PRs with explicit verification steps in the PR body.

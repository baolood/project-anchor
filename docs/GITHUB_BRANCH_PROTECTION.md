# GitHub — protect `main` with required CI checks

Goal: merges to **`main`** only happen when **`local-box-baseline`** is green, so guardrails cannot be bypassed by a direct push.

This is a **repository settings** change. It must be done by someone with **admin** (or sufficient **branch protection** permissions) on the GitHub org/repo.

See also **`docs/RELEASE_BRANCH_POLICY.md`** (branching / tags / rollback) once **`main`** protection is enabled.

## Web UI (recommended)

1. Open the repo on GitHub → **Settings** → **Branches**.
2. **Add branch protection rule** (or edit the existing rule for **`main`**).
3. **Branch name pattern:** `main`
4. Enable:
   - **Require a pull request before merging** (optional but recommended for teams).
   - **Require status checks to pass before merging**.
   - **Require branches to be up to date before merging** (optional; stricter).
5. Under **Status checks that are required**, search for and select the checks produced by **`.github/workflows/local-box-baseline.yml`**:
   - **`checklist-curl-guardrails`** (job id in the workflow file)
   - **`check`** (job id in the workflow file)
6. Save the rule.

If the check names do not appear yet, push any commit that runs the workflow once, then refresh the protection rule UI.

## Optional: GitHub CLI (`gh`)

Branch protection payloads differ by GitHub product/API version. Prefer the **web UI** above unless your org already maintains a verified **`gh api`** snippet.

If you use automation, treat it like infrastructure: pin the API contract, review diffs, and validate in a non-production repo first.

```bash
gh auth login
# Example read-only probe (adjust owner/repo):
gh api repos/<owner>/<repo>/branches/main/protection
```

## After protection is on

- Use PRs for changes to **`main`** (or allow admins-only bypass only if you accept that risk).
- After each push, optionally gate locally:

```bash
./scripts/check_local_box_ci_runs.sh --branch main --gate-strict --quiet
```

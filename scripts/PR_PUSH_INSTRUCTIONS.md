# Push feature/ops-console-minimal & Open PR

## Current state (bb1f990)

```
Branch: feature/ops-console-minimal
HEAD:   bb1f990 fix(e2e): list_retry FINAL_NOT_DONE + ops_dashboard_ui_e2e SSR/CSR compat
Remotes: none configured
```

## Steps to push

### 1) Add origin (replace with your repo URL)

```bash
# HTTPS
git remote add origin https://github.com/YOUR_ORG/project-anchor.git

# or SSH
git remote add origin git@github.com:YOUR_ORG/project-anchor.git
```

### 2) Push branch (first time use -u)

```bash
git push -u origin feature/ops-console-minimal
```

### 3) Optional: rebase onto latest main

```bash
git fetch origin
git rebase origin/main
./scripts/release_up_and_verify.sh   # re-verify after rebase
git push --force-with-lease
```

### 4) Open PR

Use the evidence below for the PR description.

---

## E2E Evidence (bb1f990)

```
./scripts/release_up_and_verify.sh exit 0
PASS_OR_FAIL=PASS
OPS_DASHBOARD_UI_E2E_PASS=YES
LIST_RETRY_UI_E2E_PASS=YES
CHECKLIST_OPS_DASHBOARD_UI_OUT=/tmp/anchor_e2e_checklist_ops_dashboard_ui_e2e_last.out
CHECKLIST_LIST_RETRY_UI_OUT=/tmp/anchor_e2e_checklist_list_retry_ui_e2e_last.out
```

Full evidence: `cat /tmp/anchor_e2e_merge_summary.out`

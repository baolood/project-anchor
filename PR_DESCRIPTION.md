# Pull request description (template)

Copy this file into the GitHub PR body and replace the placeholders. Use **repo-relative** paths and portable examples (for example `cd /path/to/project-anchor`), not machine-specific absolute paths.

## Summary

- **What:** <!-- one sentence -->
- **Why:** <!-- problem or ticket reference -->

## Scope

- **Areas touched:** <!-- e.g. local_box, scripts, anchor-backend subtree, anchor-console submodule pointer -->
- **Out of scope:** <!-- explicit non-goals -->

## How to verify

```bash
cd /path/to/project-anchor
export PYTHONPATH=.
./scripts/check_local_box_baseline.sh
```

<!-- Add service-specific steps (docker compose, UI) if relevant. -->

## Risk / rollout

- **User-visible behavior:** <!-- none / describe -->
- **Migrations / data:** <!-- N/A or describe -->
- **Submodule / subtree:** <!-- N/A or SHA bump noted -->

## Checklist

- [ ] **CI:** `local-box-baseline` (or equivalent) considered for this change
- [ ] **Docs:** `README.md` / `RUNBOOK.md` / ADRs updated if behavior or ops changed
- [ ] **Paths:** examples and scripts avoid machine-specific absolute paths (use repo-relative paths or placeholders like `/path/to/project-anchor`)
- [ ] **Secrets:** no credentials committed

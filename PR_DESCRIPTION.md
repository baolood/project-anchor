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
- [ ] **Go-live:** if you change `artifacts/go-live/`, `docs/GO_LIVE_CHECKLIST.md`, or `scripts/go_live_status_report.sh`, run `./scripts/go_live_status_report.sh` and ensure `./scripts/check_local_box_baseline.sh` still passes
- [ ] **Docs:** `README.md` / `RUNBOOK.md` / ADRs updated if behavior or ops changed
- [ ] **Paths:** examples and scripts avoid machine-specific absolute paths (use repo-relative paths or placeholders like `/path/to/project-anchor`)
- [ ] **Secrets:** no credentials committed

---

## Optional Release Summary Block (copy when needed)

Use this section when the PR is part of a hardening/governance wave and you want a release-note-friendly summary directly in the PR body.

### Hardening wave summary

- **Portable paths:** scripts/docs avoid machine-specific absolute paths.
- **Script safety:** strict bash mode and executable-bit normalization applied.
- **Checklist networking:** `curl` timeout guardrails standardized (`--connect-timeout 5 --max-time 20`).
- **CI guardrail:** dedicated `checklist-curl-guardrails` job + baseline integration.

### Recommended verifier commands

```bash
cd /path/to/project-anchor
./scripts/check_checklist_curl_guardrails.sh
./scripts/check_local_box_baseline.sh
./scripts/go_live_status_report.sh
```

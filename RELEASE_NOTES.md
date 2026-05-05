# Release notes (template)

Fill in for each tagged release. Keep examples **portable** (use `/path/to/project-anchor`, not a developer home directory).

---

## Version <!-- e.g. 0.1.0 -->

**Date:** <!-- YYYY-MM-DD -->

### Highlights

- <!-- one or two bullets for readers skimming -->

### Added

- <!-- ... -->

### Changed

- <!-- ... -->

### Fixed

- <!-- ... -->

### Ops / migration

- <!-- e.g. new env vars, SQLite path (`LOCAL_BOX_DB_PATH`), compose changes; or “None” -->

### Submodule / subtree pointers

- **anchor-console:** <!-- submodule SHA or “unchanged” -->
- **anchor-backend:** <!-- note if subtree import was refreshed -->

### Upgrade notes

```bash
cd /path/to/project-anchor
git pull
python3 -m pip install -r requirements.txt
```

<!-- Add breaking changes or manual steps above the default pull/install block if needed. -->

---

## Version hardening-wave-2026-05-05

**Date:** 2026-05-05

### Highlights

- Completed repo-wide script hardening for portability and curl timeout safety.
- Added automated checklist curl guardrail scanner and wired it into CI baseline checks.

### Added

- `scripts/check_checklist_curl_guardrails.sh` to detect checklist `curl` timeout regressions.
- Dedicated CI job `checklist-curl-guardrails` in `.github/workflows/local-box-baseline.yml`.
- Runbook guardrail section for script strict mode, portable `ROOT`, and timeout patterns.

### Changed

- Standardized shell script strict mode and executable bits across tracked scripts.
- Standardized `curl` timeout usage across checklist/e2e scripts (`--connect-timeout 5 --max-time 20`).
- Updated CI/docs wording so guardrail failures are easier to triage locally.

### Fixed

- Removed/avoided machine-specific paths in script and docs workflows.
- Hardened flaky network call behavior to avoid silent hangs in long checklist runs.

### Ops / migration

- No runtime migration required.
- Maintainers should run before merge:
  - `./scripts/check_checklist_curl_guardrails.sh`
  - `./scripts/check_local_box_baseline.sh`

### Submodule / subtree pointers

- **anchor-console:** unchanged in this hardening wave
- **anchor-backend:** unchanged in this hardening wave (no subtree refresh in this batch)

### Upgrade notes

```bash
cd /path/to/project-anchor
git pull
python3 -m pip install -r requirements.txt
./scripts/check_checklist_curl_guardrails.sh
./scripts/check_local_box_baseline.sh
```

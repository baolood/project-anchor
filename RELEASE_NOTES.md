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

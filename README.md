# Project Anchor (parent repository)

This **parent** repo holds orchestration docs, **`local_box/`**, **`shared/`**, **`risk_engine/`**, **`anchor-backend/`** (subtree), **`anchor-console/`** (submodule), and archived drafts under **`docs/archive/`**.

- **Architecture (commands / worker semantics):** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Operations / risk runbook:** [`RUNBOOK.md`](RUNBOOK.md)
- **Console (separate app):** [`anchor-console/README.md`](anchor-console/README.md)

---

## Parent repo — Python stack (`local_box`)

The **`local_box`** package (audit SQLite, control HTTP, runner) uses **repo-root** [`requirements.txt`](requirements.txt) (pinned; source constraints in [`requirements.in`](requirements.in)). Regenerate after editing pins: `python3 -m piptools compile requirements.in -o requirements.txt`.

### Setup

```bash
cd /path/to/project-anchor
python3 -m pip install -r requirements.txt
export PYTHONPATH=.
```

### SQLite database path

- **Default:** `<repository-root>/anchor.db` (see `local_box/audit/event_store.py`).
- **Override:** set **`LOCAL_BOX_DB_PATH`** to an absolute path (or use `~` expansion) if the default location is not writable.

### CI

GitHub Actions workflow **[`.github/workflows/local-box-baseline.yml`](.github/workflows/local-box-baseline.yml)** (job **`local-box-baseline`**) on **push** and **pull_request**:

1. Installs **`requirements.txt`**
2. Runs **`./scripts/check_local_box_baseline.sh`**
3. Smoke: **`event_store.init_db()`**, **`import local_box.runner`**, **`import local_box.control.server`**

### Quick local checks (after `pip install`)

```bash
export PYTHONPATH=.
python3 -c "from local_box.audit import event_store; event_store.init_db(); print(event_store.DB_PATH)"
python3 -c "import local_box.runner; print('runner ok')"
python3 -c "import local_box.control.server as c; print('control', c.app.name)"
```

More detail: **RUNBOOK.md** → section **Parent repo — `local_box` (Python + SQLite)**.

**Dependency PRs:** [Dependabot](.github/dependabot.yml) targets **repo-root** [`requirements.txt`](requirements.txt) (weekly) and **GitHub Actions** workflow pins (monthly). **Architecture note:** [`docs/adr/ADR-0004-local-box-execution-boundaries-and-naming.md`](docs/adr/ADR-0004-local-box-execution-boundaries-and-naming.md).

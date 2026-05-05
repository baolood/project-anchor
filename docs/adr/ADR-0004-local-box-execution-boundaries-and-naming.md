# ADR-0004: `local_box` execution boundaries, `risk_engine` naming, and archived `execution_service`

## Status

Accepted

## Context

The parent repository carries:

1. **`local_box/`** — audit SQLite, HTTP control plane (`local_box/control/server.py`), and a runner that dispatches work and may call an HTTP execution backend.
2. **`risk_engine/`** — contains **`client.py`**, which is **not** a risk model or rules engine. It is a **thin HTTP client** for the draft **`execution_service`** API (headers, `/execute`, `/receipt/...`). The directory name is **misleading** but is a **stable import path** today (`local_box.runner` imports `risk_engine.client`).
3. **`execution_service/`** — the exploratory Flask server and verifier were **archived** under **`docs/archive/execution_service_draft/execution_service/`** to avoid implying a production-grade service in the repo root. Archived code may still be read for history; it is **not** claimed runnable without explicit `PYTHONPATH` and companion modules.
4. **Signing** — `local_box.gate.execution_gate` must sign tickets without importing a top-level **`execution_service`** package after the archive move. **`local_box.gate.ticket_signature`** mirrors the archived verifier’s **SHA256 + shared secret** algorithm so the gate stays self-contained.

## Decision

1. **Naming vs. reality:** Treat **`risk_engine.client`** as an **execution HTTP client** in documentation and future refactors. Any rename (e.g. to `execution_client/`) requires a **follow-up ADR** and coordinated import changes (**`local_box`**, tests, CI smoke).
2. **Single source of truth for the live client:** The **tracked** client used at runtime is **`risk_engine/client.py`**. A duplicate under **`docs/archive/risk_engine_draft/`** must **not** be reintroduced.
3. **Archived `execution_service`:** Remains a **draft snapshot** only. **Archival does not** mean the stack is a **supported production microservice** in this repository layout.
4. **Ticket signatures:** **`local_box.gate.ticket_signature`** is the **authoritative signing helper** for the gate path; keep it aligned with the archived verifier if the algorithm ever changes, or replace both under one ADR.

## Consequences

- **CI** (`local-box-baseline`) continues to **`pip install -r requirements.txt`** and smoke-import **`local_box.runner`** and **`local_box.control.server`** so regressions in **`shared`**, **`risk_engine.client`**, and the gate signing path are caught early.
- **Dependabot** (see **`.github/dependabot.yml`**) may open PRs for **`requests`** / **`flask`**; review for compatibility with **`local_box`** smoke imports before merge.
- **Future work** (out of scope for this ADR): formal SDK layout, HMAC instead of toy SHA256 secret, and explicit versioning of **`shared.schemas`**.

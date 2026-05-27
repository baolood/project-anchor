# Guidance for AI / automation agents

## Defaults

- **Repo root:** assume commands run from the repository root (`cd` to the clone first).
- **Portable paths:** use repo-relative paths and placeholders like `/path/to/project-anchor`, not machine-specific home directories.

## Single source of truth

- **Go-live reporter rules (CI vs local evidence):** edit **`docs/RULES.md` first**, then update summaries in other docs if needed.
- **Machine enforcement:** **`scripts/check_go_live_rules.sh`** reads **`docs/RULES.md`** only. If you add new anchors there, update that script in the same change.

## Before proposing a merge-ready change

Run in order (matches CI job **`check`** guardrails + smokes intent):

```bash
./scripts/check_checklist_curl_guardrails.sh
./scripts/check_local_box_baseline.sh
./scripts/check_go_live_rules.sh
./scripts/go_live_status_report.sh
```

Then the Python smokes from **`README.md`** → **Quick local checks** (or **`PR_DESCRIPTION.md`** → **How to verify**).

## Backend testnet/executor rule

If a task touches **`anchor-backend/testnet/executor`** behavior, or related real/testnet executor logic under **`anchor-backend/`**, also run:

```bash
bash scripts/check_backend_testnet_executor_smoke.sh
```

Use **`scripts/check_backend_testnet_executor_smoke.sh --test <file>`** only for narrower follow-up checks; the default expectation for merge-ready validation is the full smoke set.

## Local OSS agent rule

Local OSS coding agents such as **Codex + Ollama**, **Codex --oss**, or
**llama.cpp** may be used only as draft helpers for low-risk work.

Allowed uses:

- draft docs or closeout text
- suggest small bash/script edits
- scan for repeated guardrail patterns
- draft fixture matrices
- suggest low-risk refactors for later review

Disallowed uses:

- `git commit`, `git push`, PR creation, or branch mutation
- cloud-host changes
- `env`, secret, or credential handling
- external request execution
- runtime mutation
- docker, nginx, firewall, or deploy changes
- real or simulated live-trading enablement
- real testnet send execution

Required flow:

```text
local OSS agent produces draft patch/text only
-> Codex or human reviews the draft
-> required checks run locally
-> human confirms before commit
-> explicit authorization before push
```

Use **`scripts/prepare_oss_agent_draft_prompt.sh`** to generate a safe
draft-only prompt for local OSS helpers. The helper output must be treated as
untrusted draft material until reviewed and validated inside this repository
workflow.

## Git hooks (optional for humans; agents should still run commands)

```bash
./scripts/install_git_hooks.sh
```

## CI closure

After pushing, confirm **`local-box-baseline`** is green (GitHub Actions UI or **`./scripts/check_local_box_ci_runs.sh`** with `gh` installed and authenticated).

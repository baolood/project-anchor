# Host Alignment Remediation Runbook V1

## 1. Purpose

This runbook exists to explain why a future real external request window or
bounded canary must not proceed until the Vultr host is aligned with the final
sealed mainline state.

This runbook does not authorize:

- real external request execution
- canary execution
- go-live
- live trading

## 2. Current blocked diagnosis

The blocked pre-execution check established:

- host main aligned to final seal state: NO
- host worktree clean: NO
- compose files present: YES
- correct compose working directory identified: YES
- runtime containers up: YES

Current blocker set:

- HOST_REVISION_OUTDATED
- HOST_WORKTREE_DIRTY
- PREVIOUS_COMPOSE_EXECUTION_CONTEXT_INCORRECT

## 3. Known host facts

Observed host state at the time of diagnosis:

- host repository path: `/root/project-anchor`
- host main revision: `0fe4a86`
- expected final mainline revision family: final sealed state after the final
  no-go closeouts and handoff work
- modified file present:
  - `anchor-backend/docker-compose.override.yml`
- untracked host-local artifacts present:
  - `TELEGRAM_ALERT_ACCEPTANCE_20260601-143247.txt`
  - `artifacts/g3-restore-drill/`
  - `artifacts/go-live/capacity/`
  - multiple closeout record files under `docs/`

Compose facts:

- compose files exist under:
  - `/root/project-anchor/anchor-backend/docker-compose.yml`
  - `/root/project-anchor/anchor-backend/docker-compose.override.yml`
- future compose inspection must run from:
  - `/root/project-anchor/anchor-backend`

## 4. Why the previous precheck failed

The previous precheck failed for host-state reasons, not service-health reasons.

It is not enough that `/health` or worker heartbeat looked good.

The precheck remained blocked because:

1. the host revision was materially behind the final sealed repository state
2. the host worktree was not clean
3. the compose command was previously run from the wrong directory, which made
   the result non-authoritative

## 5. Required remediation before any future window

Before any future bounded real external request window may continue past
precheck, all of the following must be true:

1. host main aligned to the intended reopen base revision: YES
2. host worktree reviewed and reconciled intentionally: YES
3. host-local artifacts preserved or explicitly classified as safe to retain: YES
4. compose checks executed from `/root/project-anchor/anchor-backend`: YES
5. compose command visibility confirmed with authoritative output: YES
6. post-alignment repo state rechecked and documented: YES

## 6. Safe remediation sequence

The future operator sequence must be:

1. capture current host repo state again
2. classify modified and untracked host-local files
3. decide what must be preserved as local evidence
4. align host repository to the intended reopen baseline without deleting
   evidence blindly
5. rerun compose visibility and `docker compose ps` from
   `/root/project-anchor/anchor-backend`
6. rerun read-only health and ops checks
7. only then revisit Real External Request Window Pre-Execution Check

No real external request may be sent during this remediation sequence.

## 7. Mandatory stop conditions

Stop immediately if:

- the host revision is still behind the intended reopen baseline
- dirty files cannot be explained safely
- evidence preservation would be lost by sync
- compose commands are still being run from the wrong directory
- authoritative compose visibility cannot be established
- any step would implicitly trigger real external request execution

## 8. Explicit non-claims

- this runbook does not reopen the authorization chain
- this runbook does not authorize a future bounded window
- this runbook does not authorize a canary
- this runbook does not authorize go-live
- this runbook does not authorize live trading

## 9. Final remediation status

- host alignment remediation runbook prepared: YES
- host main aligned to final seal state now: NO
- host worktree clean now: NO
- compose working directory requirement fixed: YES
- real external request remains blocked: YES

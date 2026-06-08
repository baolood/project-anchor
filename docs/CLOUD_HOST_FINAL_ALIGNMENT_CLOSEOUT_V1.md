# Cloud host final alignment closeout V1

**Status:** final cloud-host alignment closeout - stage host runtime aligned to current `main`; canonical testnet runtime contract aligned; canary not authorized; go-live remains NO-GO; live trading remains NO-GO.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-06-08**

**Scope:** close the bounded engineering alignment round that brought the Vultr stage host checkout, backend / worker runtime, persistent testnet env-file wiring, and canonical `TESTNET_*` contract into one consistent state after the post-merge cleanup PR for the legacy `BINANCE_*` bridge.

This document does not authorize canary execution, production launch, or live trading.
It records one bounded cloud-host alignment result only.

## 1. Target host

- `provider_role`: `Vultr Project Anchor stage host`
- `public_ip`: `45.76.190.109`
- `hostname`: `vultr`
- `repo_path`: `/root/project-anchor`
- `backend_compose_path`: `/root/project-anchor/anchor-backend`

## 2. Revision alignment

The host checkout was first observed behind current `main`:

- `previous_host_head`: `c199af7`

The host was then fast-forwarded to the current merged state:

- `aligned_host_head`: `963f99e`

This aligned host revision includes the merged cleanup for the canonical testnet runtime contract:

- `cleanup_pr`: `#138`
- `cleanup_subject`: `Remove legacy Binance testnet env bridge`

## 3. Runtime alignment result

After the bounded rebuild / worker recycle with the persistent env-file:

- `persistent_env_file_path`: `/etc/project-anchor/testnet.env`
- `compose_bringup_mode`: `docker compose --env-file /etc/project-anchor/testnet.env up -d --build`
- `worker_recycle_mode`: `docker compose --env-file /etc/project-anchor/testnet.env up -d worker`

The live runtime surfaces reported:

- `/health`: `PASS`
- `/ops/state`: `PASS`
- `/ops/worker`: `PASS`
- `kill_switch_enabled`: `false`
- `worker_heartbeat`: `PASS`
- `telegram_enabled`: `true`

The live backend / worker canonical testnet posture reported:

- `TESTNET_EXCHANGE_BASE_URL`: `https://demo-fapi.binance.com`
- `TESTNET_EXCHANGE_API_KEY`: present
- `TESTNET_EXCHANGE_API_SECRET`: present
- `TESTNET_EXCHANGE_KEY_ID`: present
- `TESTNET_EXECUTOR_MODE`: `real`
- `TESTNET_EXECUTOR_REAL_ENABLE`: `1`

## 4. Strict alignment verdict

The repository alignment checker reported:

```text
CLOUD_HOST_RUNTIME_ENV_ALIGNMENT PASS: canonical_testnet_runtime_aligned
```

The relevant resolved facts were:

- `REPO_LEGACY_OVERRIDE_PRESENT=no`
- `REPO_CANONICAL_TESTNET_OVERRIDE_PRESENT=yes`
- `RUNTIME_BACKEND_TESTNET_ENV_PRESENT=yes`
- `RUNTIME_WORKER_TESTNET_ENV_PRESENT=yes`
- `RUNTIME_WORKER_LEGACY_BINANCE_ENV_PRESENT=no`

This means the host is no longer only “functionally aligned”.
It is now also aligned under the stricter canonical-runtime checker.

## 5. Residual host-local note

Host git status still includes one untracked artifact directory:

- `artifacts/early-invocation-reconciliation/`

Observed contents:

- `artifacts/early-invocation-reconciliation/20260605T165009+0800/backend_tail.txt`
- `artifacts/early-invocation-reconciliation/20260605T165009+0800/early_invocation_reconciliation_summary.txt`
- `artifacts/early-invocation-reconciliation/20260605T165009+0800/worker_tail.txt`

This untracked directory did not block runtime alignment and was not mutated by this closeout.

## 6. Final verdict

The correct final conclusion for this bounded cloud-host alignment round is:

- `cloud_host_runtime_liveness`: `PASS`
- `cloud_host_revision_alignment`: `PASS`
- `cloud_host_canonical_testnet_runtime_alignment`: `PASS`
- `overall`: `PASS`

## 7. Boundary statement

This closeout does **not** authorize production execution.

The correct boundary remains:

- `canary`: `NOT AUTHORIZED`
- `go-live`: `NO-GO`
- `live trading`: `NO-GO`

## 8. Stable status statement

At this point the correct stable summary is:

```text
cloud host:
aligned to current main
aligned to canonical TESTNET_* runtime contract
/health PASS
/ops/state PASS
/ops/worker PASS
kill switch false
worker heartbeat fresh
telegram enabled true
canary: NOT AUTHORIZED
go-live: NO-GO
live trading: NO-GO
```

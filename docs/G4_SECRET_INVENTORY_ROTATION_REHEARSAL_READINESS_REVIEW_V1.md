# G4 Secret Inventory And Rotation Rehearsal Readiness Review V1

## 1) Review question

This review answers one narrow question:

- is the current `Secret management and key rotation policy` row ready to
  proceed to a real secret rotation rehearsal?

This review does not rotate a secret, does not mutate host/runtime
configuration, and does not change any live credential.

## 2) Current fixed gate state

- `G1 — Deployment and rollback drills pass`: DONE
- `G2 — P0/P1 alerting verified`: DONE
- `G3 — Backup/restore drill within RPO/RTO`: DONE
- `G4 — Security review complete (secrets + permissions + vuln baseline)`:
  NOT_DONE
- go-live: NO-GO
- real external request: NOT AUTHORIZED
- live trading: NO-GO

## 3) Inputs reviewed

Primary Week 5-6 security row:

- **`docs/GO_LIVE_CHECKLIST.md`** → `Secret management and key rotation policy`

Primary draft reviewed:

- **`docs/SECRETS_AND_ROTATION.md`**

Related reference reviewed for pattern support:

- **`docs/TESTNET_SECRETS_CUSTODY_V1.md`**

## 4) Current evidence status

### 4.1 Secret inventory completeness

Current state:

- NOT_READY

Why:

- the inventory table exists
- but multiple storage locations are still placeholder values such as
  `<TBD secret manager>` / `<TBD>`
- the row is therefore structurally present but not operationally complete

### 4.2 No-plaintext verification readiness

Current state:

- READY_TO_RUN

Why:

- the draft already defines a concrete parent-repo scan command
- scope rules are documented
- expected interpretation of findings is documented

But still missing:

- an actual recorded scan result for the current release line

### 4.3 Rotation rehearsal readiness

Current state:

- NOT_READY

Why:

- the draft recommends `SEC-CI` as the first rehearsal candidate
- the general pre/rotate/post path is documented
- but there is no completed operator-ready rehearsal record yet
- there is no concrete evidence bundle proving one specific secret can be
  rotated end-to-end under current boundaries

## 5) Readiness decision

Current row reviewed:

- `Secret management and key rotation policy`

Decision:

- NOT_READY for real rotation rehearsal

Blocking gaps:

1. inventory not yet fully filled with concrete storage locations / owner facts
2. no current recorded no-plaintext scan result
3. no rehearsal-specific execution packet for one chosen secret

## 6) Safe next task

Next task type:

- docs-only

Next task name:

- `G4 Secret Inventory Completion And Rehearsal Packet V1`

Allowed files:

- `docs/G4_SECRET_INVENTORY_COMPLETION_AND_REHEARSAL_PACKET_V1.md`
- `docs/SECRETS_AND_ROTATION.md`
- `docs/GO_LIVE_CHECKLIST.md`

Forbidden files/actions:

- `anchor-backend/**`
- `anchor-console/**`
- `docker-compose*`
- `migrations/**`
- `scripts/**`
- `.github/**`
- any env files
- any runtime config
- any generated runtime artifact
- any real secret rotation
- any host/CI secret mutation

The next task should:

1. choose the single first rehearsal candidate (`SEC-CI` unless evidence in
   repo says otherwise)
2. complete inventory fields needed for that candidate
3. define the exact evidence packet for a future rehearsal
4. keep the row `NOT_DONE`

## 7) Explicit non-claims

- This review does not complete `Secret management and key rotation policy`.
- This review does not complete `G4`.
- This review does not authorize real secret rotation.
- This review does not authorize go-live.
- This review does not authorize live trading.
- This review does not authorize real external requests.

## 8) Final review result

- reviewed row: `Secret management and key rotation policy`
- inventory complete enough for rehearsal: NO
- no-plaintext scan definition exists: YES
- recorded no-plaintext scan result exists: NO
- rehearsal candidate chosen in current draft: YES
- real rotation rehearsal may start now: NO
- next task should remain docs-only: YES

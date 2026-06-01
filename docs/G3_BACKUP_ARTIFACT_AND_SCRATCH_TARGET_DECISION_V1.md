# G3 Backup Artifact And Scratch Target Decision V1

## Current G3 precheck result

- G3 — Backup/restore drill within RPO/RTO: NOT_DONE
- actual restore drill executed: NO
- production overwrite authorized: NO
- bounded restore target implemented: NO
- backup artifact presence verified: NO
- proceed to first bounded restore drill: NO
- live trading: NO-GO
- real external request: NOT AUTHORIZED

## Precheck evidence summary

Observed facts from the latest bounded restore drill precheck:

- host: vultr
- repo: /root/project-anchor
- revision: 0fe4a86
- postgres container: anchor-backend-postgres-1
- active data volume: anchor-backend_pgdata -> /var/lib/postgresql/data
- visible databases: anchor, postgres, template0, template1
- no existing scratch restore DB target observed
- no verified restore artifact observed in common local paths

These facts are sufficient to show that the first bounded restore drill must
not proceed yet.

## Backup artifact decision

Decision:

- first drill must use an explicitly generated or explicitly selected bounded
  backup artifact
- artifact must be stored outside production data volume
- artifact path must be recorded before restore
- artifact must not expose secrets
- artifact presence must be verified by command output before restore
- missing artifact is a STOP condition

This decision does **not** claim that the artifact already exists.

## Scratch restore target decision

Decision:

- first drill restore target must be a new bounded scratch database, not
  production `anchor`
- recommended target name: anchor_restore_drill_scratch
- target must be verified as non-production before restore
- restore must never point to database name `anchor`
- target identity must be printed and recorded before restore
- unclear target identity is a STOP condition

This task does **not** create the database.

## Required future pre-execution checks

The future execution-preflight evidence must include:

- git state before drill
- active postgres container
- production database identity
- scratch database absence/presence
- backup artifact path
- backup artifact size/checksum or equivalent proof
- target database name
- explicit confirmation that target != anchor

## Mandatory stop conditions

The future drill must stop if:

- backup artifact is missing
- backup artifact path is ambiguous
- target database is anchor
- target identity is unclear
- command would overwrite production
- production data volume would be modified directly
- secrets would be printed
- host dirty state is unexplained
- restore command is not reviewable before execution

## G3 status after this decision

- backup artifact decision prepared: YES
- scratch restore target decision prepared: YES
- backup artifact presence verified: NO
- scratch target implemented: NO
- actual restore drill executed: NO
- RPO measured: NO
- RTO measured: NO
- G3 ready for DONE: NO

## Explicit non-claims

- This decision does not prove backup exists
- This decision does not prove restore works
- This decision does not satisfy G3
- This decision does not authorize production overwrite
- This decision does not authorize live trading
- This decision does not authorize external requests

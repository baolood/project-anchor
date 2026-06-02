# Go-Live Remaining Hard Gates Selection V1

## 1) Current fixed completed gates

- `G2 — P0/P1 alerting verified`: DONE
- `G3 — Backup/restore drill within RPO/RTO`: DONE

## 2) Still-forbidden boundaries

- real external request: NOT AUTHORIZED
- live trading: NO-GO
- go-live: NO-GO
- production overwrite: NO

## 3) Remaining hard gates inventory

Remaining NOT_DONE hard gates from the current
**`docs/GO_LIVE_CHECKLIST.md`**:

1. `G1 — Deployment and rollback drills pass`
2. `G4 — Security review complete (secrets + permissions + vuln baseline)`
3. `G5 — Capacity/stress test at target load pass`
4. `G6 — On-call roster + incident SOP active`

This inventory is read directly from the current checklist. No additional hard
gates are invented here, and none of the remaining gates are marked DONE by
this document.

## 4) Next selected gate

Selected next mainline gate:

- `G1 — Deployment and rollback drills pass`

Selected gate status:

- NOT_DONE

## 5) Why this gate is next

`G1` is still blocking go-live because it appears first in the remaining hard
gate order and it represents the operational ability to deploy and recover
without ambiguity.

What evidence is still missing at the hard-gate level:

- an explicit gate-level reconciliation that ties the already-recorded Week 2
  deploy validation and rollback drill evidence to the hard gate row itself
- a single closeout statement that says whether the current evidence already
  satisfies `G1`, rather than leaving the gate as an unchecked row in the
  checklist

What must not be done yet:

- do not mark `G1` DONE by this selection record
- do not start `G4`, `G5`, or `G6` before resolving the highest-priority
  remaining gate
- do not authorize go-live, live trading, or real external requests

## 6) Next task boundary

Next task type:

- docs-only

Next task name:

- `G1 Deployment And Rollback Gate Reconciliation Review V1`

Allowed files:

- `docs/G1_DEPLOYMENT_ROLLBACK_GATE_RECONCILIATION_REVIEW_V1.md`
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
- any deploy, rollback, or host-side execution

Validation commands:

- `git diff --check`
- `grep -n "G1 — Deployment and rollback drills pass" docs/GO_LIVE_CHECKLIST.md`
- `grep -n "Selected next mainline gate:" docs/GO_LIVE_REMAINING_HARD_GATES_SELECTION_V1.md`
- `grep -n "G1 — Deployment and rollback drills pass" docs/GO_LIVE_REMAINING_HARD_GATES_SELECTION_V1.md`
- `git status --short`

Acceptance criteria:

- the next task reads current Week 2 deploy and rollback evidence only
- the next task determines whether `G1` can honestly move to DONE
- the next task does not run any runtime action
- the next task preserves:
  - go-live: NO-GO
  - live trading: NO-GO
  - real external request: NOT AUTHORIZED

Rollback method:

- if the next task is incorrect before merge:
  - `git restore docs/G1_DEPLOYMENT_ROLLBACK_GATE_RECONCILIATION_REVIEW_V1.md docs/GO_LIVE_CHECKLIST.md`
- if merged and later found incorrect:
  - `git revert <commit>`

## 7) Explicit non-claims

- This selection does not authorize go-live.
- This selection does not authorize live trading.
- This selection does not authorize real external requests.
- This selection does not complete the selected gate.
- This selection does not modify runtime behavior.
